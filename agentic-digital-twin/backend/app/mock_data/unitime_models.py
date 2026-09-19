"""
Mock UniTime-shaped scheduling data — companion to models.py (the CMS/SAP-shaped
academic records DB).

UniTime (unitime.org, Apereo Foundation) is open source, so this isn't a guess —
it mirrors UniTime's actual, well-documented domain concepts:
  AcademicSession -> SubjectArea -> InstructionalOffering -> Class_
  Class_ -> Assignment (room + time pattern + instructor)
  Class_ -> StudentClassEnrollment (which student sits in which section)

NOTE: table/column NAMES here are a reasonable mock, not a byte-for-byte copy
of UniTime's internal Hibernate schema (that lives in UniTime's Java source,
github.com/UniTime/unitime, under JavaSource/org/unitime/timetable/model —
worth checking directly if you need an exact match later). The relationships
and cardinalities below do reflect how UniTime actually structures scheduling.

Timetabling/scheduling logic itself is OUT OF SCOPE for the Digital Twin app
(per your FYP scope) — this only exists so other modules (e.g. Academics &
University Life) can display a student's class schedule, room, and timing
without needing live UniTime API access.
"""

import enum
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Enum, Time,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DayOfWeek(enum.Enum):
    MON = "Mon"
    TUE = "Tue"
    WED = "Wed"
    THU = "Thu"
    FRI = "Fri"
    SAT = "Sat"


class ClassType(enum.Enum):
    LECTURE = "Lecture"
    LAB = "Lab"
    SEMINAR = "Seminar"
    TUTORIAL = "Tutorial"


class RoomType(enum.Enum):
    CLASSROOM = "Classroom"
    LAB = "Lab"
    SEMINAR_ROOM = "Seminar Room"
    AUDITORIUM = "Auditorium"


class EnrollmentStatus(enum.Enum):
    ENROLLED = "enrolled"
    WAITLISTED = "waitlisted"
    DROPPED = "dropped"


# --------------------------------------------------------------------------
# Session / Subject Area — UniTime's top-level scoping (mirrors your Semester
# and Department tables from models.py, kept separate since UniTime treats
# scheduling as its own system of record)
# --------------------------------------------------------------------------

class AcademicSession(Base):
    __tablename__ = "academic_sessions"

    id = Column(Integer, primary_key=True)
    label = Column(String(30), unique=True, nullable=False)   # e.g. "Fall 2026"
    academic_year = Column(String(9), nullable=False)          # e.g. "2026-2027"
    is_current = Column(Boolean, default=False)

    subject_areas = relationship("SubjectArea", back_populates="session")


class SubjectArea(Base):
    __tablename__ = "subject_areas"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("academic_sessions.id"), nullable=False)
    abbreviation = Column(String(10), nullable=False)   # e.g. "CS"
    title = Column(String(120), nullable=False)         # e.g. "Computer Science"

    session = relationship("AcademicSession", back_populates="subject_areas")
    offerings = relationship("InstructionalOffering", back_populates="subject_area")


# --------------------------------------------------------------------------
# Rooms — UniTime's central shared resource
# --------------------------------------------------------------------------

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    building = Column(String(60), nullable=False)
    room_number = Column(String(20), nullable=False)
    capacity = Column(Integer, nullable=False)
    room_type = Column(Enum(RoomType), nullable=False)
    has_projector = Column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("building", "room_number"),)

    assignments = relationship("Assignment", back_populates="room")


# --------------------------------------------------------------------------
# Instructional Offering -> Class_  (the course "exists" here; a Class_ is a
# schedulable section of it — lecture, lab, etc. UniTime keeps this separate
# from the CMS course catalog, which is why it's duplicated conceptually
# from Course in models.py rather than merged into it)
# --------------------------------------------------------------------------

class InstructionalOffering(Base):
    __tablename__ = "instructional_offerings"

    id = Column(Integer, primary_key=True)
    subject_area_id = Column(Integer, ForeignKey("subject_areas.id"), nullable=False)
    course_number = Column(String(10), nullable=False)   # e.g. "721"
    course_title = Column(String(150), nullable=False)
    external_course_code = Column(String(20))
    # links back to the CMS/SAP mock DB's Course.code (models.py) — kept as a
    # plain string reference rather than a cross-database FK, since the two
    # systems are integrated, not merged, in a real institutional setup.

    subject_area = relationship("SubjectArea", back_populates="offerings")
    classes = relationship("Class_", back_populates="offering")


class Class_(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True)
    offering_id = Column(Integer, ForeignKey("instructional_offerings.id"), nullable=False)
    section_number = Column(String(10), nullable=False)   # e.g. "01", "L1"
    class_type = Column(Enum(ClassType), nullable=False)
    limit = Column(Integer, nullable=False)   # max seats
    instructor_external_id = Column(String(10))
    # links back to Faculty.sap_id (models.py)

    offering = relationship("InstructionalOffering", back_populates="classes")
    assignment = relationship("Assignment", back_populates="class_", uselist=False)
    enrollments = relationship("StudentClassEnrollment", back_populates="class_")


# --------------------------------------------------------------------------
# Assignment — the actual solved timetable slot: room + day/time pattern
# --------------------------------------------------------------------------

class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("classes.id"), unique=True, nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    days = Column(String(15), nullable=False)     # e.g. "Mon,Wed" — UniTime encodes as a bitmask; kept readable here
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    class_ = relationship("Class_", back_populates="assignment")
    room = relationship("Room", back_populates="assignments")


# --------------------------------------------------------------------------
# Student Class Enrollment — which student sits in which section
# (cross-references Student.sap_id from models.py rather than duplicating
# the Student table, same integration pattern as instructor_external_id)
# --------------------------------------------------------------------------

class StudentClassEnrollment(Base):
    __tablename__ = "student_class_enrollments"
    __table_args__ = (UniqueConstraint("student_external_id", "class_id"),)

    id = Column(Integer, primary_key=True)
    student_external_id = Column(String(10), nullable=False)   # links to Student.sap_id
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    status = Column(Enum(EnrollmentStatus), default=EnrollmentStatus.ENROLLED)

    class_ = relationship("Class_", back_populates="enrollments")
