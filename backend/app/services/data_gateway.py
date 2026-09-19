"""
data_gateway.py — the swappable data-access layer for the Digital Twin.

WHY THIS FILE EXISTS
---------------------
Right now we have no production API access to CMS/SAP, UniTime, or LMS. So
every other part of the app (agent tools, API routes, chat handlers) should
NEVER talk to twin_mock.db / unitime_mock.db directly, and should NEVER call
a real SAP/UniTime API directly either. They should only talk to the
DataGateway interface below.

Today: DataGateway = MockDataGateway (reads the two SQLite mock DBs).
Later: swap in a RealDataGateway that calls the actual CMS/SAP + UniTime REST
       APIs instead. The interface (method names, inputs, outputs) stays
       identical — so nothing that calls this file needs to change.

This is the Adapter/Repository pattern. One switch point, not scattered
"if mock else real" checks all over your codebase.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import os
import sqlite3


# --------------------------------------------------------------------------
# Data shapes returned to the rest of the app — these stay the same
# regardless of which gateway implementation is active.
# --------------------------------------------------------------------------

@dataclass
class StudentProfile:
    sap_id: str
    full_name: str
    program_name: str
    cgpa: float
    status: str
    current_semester: int
    advisor_name: Optional[str]


@dataclass
class ClassSchedule:
    course_code: str
    course_title: str
    section_type: str      # "Lecture" / "Lab"
    days: str               # e.g. "Mon,Wed"
    start_time: str
    end_time: str
    building: str
    room_number: str


# --------------------------------------------------------------------------
# The interface. Every gateway implementation MUST provide these methods
# with these exact signatures.
# --------------------------------------------------------------------------

class DataGateway(ABC):

    @abstractmethod
    def get_student_profile(self, sap_id: str) -> Optional[StudentProfile]:
        """Return the student's core profile, or None if the SAP ID doesn't exist."""

    @abstractmethod
    def get_class_schedule(
        self, sap_id: str, course_name_contains: Optional[str] = None
    ) -> list[ClassSchedule]:
        """
        Return the student's scheduled classes for the current term.
        If course_name_contains is given, filter to courses whose title or
        code contains that text (case-insensitive) — e.g. "DBMS", "Database".
        """


# --------------------------------------------------------------------------
# MockDataGateway — today's implementation, reads the two SQLite mock DBs.
# --------------------------------------------------------------------------

class MockDataGateway(DataGateway):

    def __init__(self, cms_db_path: str = None, unitime_db_path: str = None):
        base = os.path.dirname(os.path.abspath(__file__))
        mock_data_dir = os.path.join(base, "..", "mock_data")
        self.cms_db_path = cms_db_path or os.path.join(mock_data_dir, "twin_mock.db")
        self.unitime_db_path = unitime_db_path or os.path.join(mock_data_dir, "unitime_mock.db")

    def _cms_conn(self):
        conn = sqlite3.connect(self.cms_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _unitime_conn(self):
        conn = sqlite3.connect(self.unitime_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_student_profile(self, sap_id: str) -> Optional[StudentProfile]:
        conn = self._cms_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.sap_id, s.full_name, s.cgpa, s.status, s.current_semester,
                   p.name AS program_name, f.full_name AS advisor_name
            FROM students s
            JOIN programs p ON s.program_id = p.id
            LEFT JOIN faculty f ON s.advisor_id = f.id
            WHERE s.sap_id = ?
        """, (sap_id,))
        row = cur.fetchone()
        conn.close()

        if row is None:
            return None

        return StudentProfile(
            sap_id=row["sap_id"],
            full_name=row["full_name"],
            program_name=row["program_name"],
            cgpa=row["cgpa"],
            status=row["status"],
            current_semester=row["current_semester"],
            advisor_name=row["advisor_name"],
        )

    def get_class_schedule(
        self, sap_id: str, course_name_contains: Optional[str] = None
    ) -> list[ClassSchedule]:
        # Step 1: from the CMS mock DB, find which course codes this student
        # is enrolled in for the CURRENT semester only. Scoping to the
        # current semester matters: without it, a student who took (or is
        # retaking) a same-named course in an earlier term would show up
        # here too, and we'd have no way to tell which one is "now".
        cms_conn = self._cms_conn()
        cur = cms_conn.cursor()
        query = """
            SELECT DISTINCT c.code
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            JOIN semesters sem ON e.semester_id = sem.id
            WHERE s.sap_id = ? AND sem.is_current = 1
        """
        params = [sap_id]
        if course_name_contains:
            query += " AND (c.title LIKE ? OR c.code LIKE ?)"
            like = f"%{course_name_contains}%"
            params += [like, like]
        cur.execute(query, params)
        enrolled_codes = [row["code"] for row in cur.fetchall()]
        cms_conn.close()

        if not enrolled_codes:
            return []

        # Step 2: from the UniTime mock DB, find the EXACT section this
        # student is registered in — via student_class_enrollments, not by
        # matching course code alone. This is what correctly disambiguates:
        # if "DBMS" exists as separate Semester-1 and Semester-4 sections
        # (different cohorts, possibly different room/time/instructor), the
        # student's own enrollment record pins them to exactly one class_id,
        # so we never guess between sections — we look up the one that's
        # actually theirs. We also scope to the current academic session and
        # to status = 'enrolled' (excluding dropped/waitlisted registrations).
        unitime_conn = self._unitime_conn()
        cur = unitime_conn.cursor()
        placeholders = ",".join("?" for _ in enrolled_codes)
        cur.execute(f"""
            SELECT io.external_course_code, io.course_title, c.class_type,
                   a.days, a.start_time, a.end_time, r.building, r.room_number
            FROM student_class_enrollments sce
            JOIN classes c ON sce.class_id = c.id
            JOIN instructional_offerings io ON c.offering_id = io.id
            JOIN subject_areas sa ON io.subject_area_id = sa.id
            JOIN academic_sessions sess ON sa.session_id = sess.id
            JOIN assignments a ON a.class_id = c.id
            JOIN rooms r ON a.room_id = r.id
            WHERE sce.student_external_id = ?
              AND sess.is_current = 1
              AND sce.status = 'ENROLLED'
              AND io.external_course_code IN ({placeholders})
        """, [sap_id] + enrolled_codes)

        results = [
            ClassSchedule(
                course_code=row["external_course_code"],
                course_title=row["course_title"],
                section_type=row["class_type"],
                days=row["days"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                building=row["building"],
                room_number=row["room_number"],
            )
            for row in cur.fetchall()
        ]
        unitime_conn.close()
        return results


# --------------------------------------------------------------------------
# RealDataGateway — STUB for later, once real API access exists.
# Same method signatures as MockDataGateway. Fill these in when you have
# actual SAP/UniTime API credentials/endpoints; nothing else in the app
# needs to change.
# --------------------------------------------------------------------------

class RealDataGateway(DataGateway):

    def __init__(self, sap_api_base_url: str, unitime_api_base_url: str, api_key: str):
        self.sap_api_base_url = sap_api_base_url
        self.unitime_api_base_url = unitime_api_base_url
        self.api_key = api_key

    def get_student_profile(self, sap_id: str) -> Optional[StudentProfile]:
        # TODO: replace with a real HTTP call once SAP API access exists, e.g.:
        # response = requests.get(f"{self.sap_api_base_url}/students/{sap_id}",
        #                          headers={"Authorization": f"Bearer {self.api_key}"})
        # ...map response JSON into a StudentProfile
        raise NotImplementedError("RealDataGateway not wired up yet — use MockDataGateway")

    def get_class_schedule(
        self, sap_id: str, course_name_contains: Optional[str] = None
    ) -> list[ClassSchedule]:
        # TODO: real UniTime API call goes here, same idea as above
        raise NotImplementedError("RealDataGateway not wired up yet — use MockDataGateway")


# --------------------------------------------------------------------------
# This is the ONE line the rest of your app imports and depends on.
# To go live with real data later, change ONLY this line.
# --------------------------------------------------------------------------

def get_gateway() -> DataGateway:
    return MockDataGateway()
    # later: return RealDataGateway(sap_api_base_url="...", unitime_api_base_url="...", api_key="...")
