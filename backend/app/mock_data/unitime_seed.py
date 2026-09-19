"""
unitime_seed.py — populate the mock UniTime-shaped scheduling DB.

Reads students/faculty/courses/departments FROM your existing twin_mock.db
(built by seed.py) so both mock systems agree with each other — same SAP IDs,
same course codes — mirroring how UniTime would really integrate with a CMS.

Run:  python unitime_seed.py --reset
Requires twin_mock.db to already exist (run seed.py first).
"""

import argparse
import random
import sqlite3
from datetime import time

from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from unitime_models import (
    Base, AcademicSession, SubjectArea, Room, InstructionalOffering, Class_,
    Assignment, StudentClassEnrollment,
    ClassType, RoomType, EnrollmentStatus,
)

fake = Faker()
random.seed(7)
Faker.seed(7)

CMS_DB_PATH = "twin_mock.db"
UNITIME_DB_PATH = "sqlite:///unitime_mock.db"

BUILDINGS = ["Main Academic Block", "Faculty of Computing Building", "Research Annex"]
DAY_PATTERNS = ["Mon,Wed", "Tue,Thu", "Mon,Wed,Fri", "Wed", "Sat"]
TIME_SLOTS = [
    (time(8, 30), time(9, 45)), (time(10, 0), time(11, 15)),
    (time(11, 30), time(12, 45)), (time(14, 0), time(15, 15)),
    (time(15, 30), time(16, 45)), (time(17, 0), time(18, 15)),
]


def load_from_cms():
    """Pull departments/courses/faculty/students out of the CMS mock DB (read-only)."""
    conn = sqlite3.connect(CMS_DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM departments")
    departments = cur.fetchall()

    cur.execute("SELECT id, code, title, department_id, instructor_id FROM courses")
    courses = cur.fetchall()

    cur.execute("SELECT id, sap_id FROM faculty")
    faculty = cur.fetchall()
    faculty_by_id = {f["id"]: f["sap_id"] for f in faculty}

    cur.execute("SELECT id, sap_id, program_id FROM students WHERE status != 'WITHDRAWN'")
    students = cur.fetchall()

    # Each student's ACTUAL current-semester course codes — this is what
    # makes the two mock DBs agree with each other. Without this, UniTime
    # enrollments would be sampled at random and wouldn't match what the
    # CMS says the student is actually taking this term.
    cur.execute("""
        SELECT s.sap_id, c.code
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        JOIN semesters sem ON e.semester_id = sem.id
        WHERE sem.is_current = 1
    """)
    current_enrollments_by_sap_id = {}
    for row in cur.fetchall():
        current_enrollments_by_sap_id.setdefault(row["sap_id"], []).append(row["code"])

    conn.close()
    return departments, courses, faculty_by_id, students, current_enrollments_by_sap_id


def build(session, departments, courses, faculty_by_id, students, current_enrollments_by_sap_id):
    # ---- Academic session (current term only, keeps this focused) ----
    sess = AcademicSession(label="Fall 2026", academic_year="2026-2027", is_current=True)
    session.add(sess)
    session.flush()

    # ---- Subject areas, one per CMS department ----
    subject_area_by_dept_id = {}
    for dept in departments:
        abbrev = "".join(w[0] for w in dept["name"].split()[-2:]).upper()[:4]
        sa = SubjectArea(session_id=sess.id, abbreviation=abbrev, title=dept["name"])
        session.add(sa)
        session.flush()
        subject_area_by_dept_id[dept["id"]] = sa

    # ---- Rooms ----
    rooms = []
    for building in BUILDINGS:
        for floor in range(1, 4):
            for room_no in range(1, 5):
                r = Room(
                    building=building,
                    room_number=f"{floor}{room_no:02d}",
                    capacity=random.choice([30, 40, 60, 90, 150]),
                    room_type=random.choices(
                        list(RoomType), weights=[0.55, 0.2, 0.15, 0.1]
                    )[0],
                    has_projector=random.random() < 0.85,
                )
                session.add(r)
                rooms.append(r)
    session.flush()

    # ---- Instructional offerings + classes + assignments, from CMS courses ----
    class_by_course_code = {}
    for course in courses:
        sa = subject_area_by_dept_id[course["department_id"]]
        offering = InstructionalOffering(
            subject_area_id=sa.id,
            course_number=course["code"].split("-")[-1],
            course_title=course["title"],
            external_course_code=course["code"],
        )
        session.add(offering)
        session.flush()

        instructor_ext_id = faculty_by_id.get(course["instructor_id"])
        # A lecture section, and ~40% chance of an accompanying lab section
        section_types = [ClassType.LECTURE]
        if random.random() < 0.4:
            section_types.append(ClassType.LAB)

        offering_classes = []
        for i, ctype in enumerate(section_types):
            cls = Class_(
                offering_id=offering.id,
                section_number=f"{i + 1:02d}",
                class_type=ctype,
                limit=random.choice([30, 40, 60]),
                instructor_external_id=instructor_ext_id,
            )
            session.add(cls)
            session.flush()

            room = random.choice(rooms)
            days = random.choice(DAY_PATTERNS)
            start, end = random.choice(TIME_SLOTS)
            session.add(Assignment(
                class_id=cls.id, room_id=room.id,
                days=days, start_time=start, end_time=end,
            ))
            offering_classes.append(cls)

        class_by_course_code[course["code"]] = offering_classes

    session.flush()

    # ---- Student class enrollments — MUST match each student's actual
    # current-semester CMS enrollments (current_enrollments_by_sap_id), not
    # a random sample. This is what lets get_class_schedule() correctly
    # disambiguate between look-alike sections (e.g. a Semester-1 DBMS
    # section vs a Semester-4 DBMS section) by following the student's own
    # enrollment record instead of guessing from the course title. ----
    for student in students:
        codes_this_term = current_enrollments_by_sap_id.get(student["sap_id"], [])
        for code in codes_this_term:
            classes = class_by_course_code.get(code)
            if not classes:
                continue
            cls = random.choice(classes)
            status = random.choices(
                list(EnrollmentStatus), weights=[0.85, 0.1, 0.05]
            )[0]
            try:
                session.add(StudentClassEnrollment(
                    student_external_id=student["sap_id"],
                    class_id=cls.id,
                    status=status,
                ))
            except Exception:
                continue

    session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    departments, courses, faculty_by_id, students, current_enrollments_by_sap_id = load_from_cms()

    engine = create_engine(UNITIME_DB_PATH)
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    build(session, departments, courses, faculty_by_id, students, current_enrollments_by_sap_id)
    session.close()

    print(f"Seeded {UNITIME_DB_PATH} — {len(courses)} offerings scheduled across "
          f"rooms/time slots, enrollments generated for {len(students)} students.")


if __name__ == "__main__":
    main()
