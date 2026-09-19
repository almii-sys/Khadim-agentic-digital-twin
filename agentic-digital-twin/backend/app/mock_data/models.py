"""
Mock institutional database schema — AI Agentic Digital Twin for Program Coordination.

Mirrors the shape of a real CMS/SAP + LMS student-lifecycle system for
Graduate & Postgraduate Computing programs, WITHOUT containing any real
student/faculty data. Structure only; all rows are synthetic (see seed.py).

Modules covered:
  1. Admissions & Program Exploration      -> Program, AdmissionApplication
  2. Academics & University Life           -> Department, Faculty, Course, Enrollment, Semester
  3. Degree Progress & Academic Standing    -> AcademicStanding
  4. Research & Thesis Journey              -> Thesis, ThesisMilestone
  5. Degree Completion & Graduation         -> GraduationClearance
  6. Forms & Documents                      -> DocumentRequest
"""


import enum

from sqlalchemy import (
    Column, Integer, String, Float, Date, Boolean, ForeignKey, Enum, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# --------------------------------------------------------------------------
# Shared enums
# --------------------------------------------------------------------------

class ProgramLevel(enum.Enum):
    MS = "MS"
    MPHIL = "MPhil"
    PHD = "PhD"


class StudentStatus(enum.Enum):
    ACTIVE = "active"
    ON_PROBATION = "on_probation"
    WITHDRAWN = "withdrawn"
    GRADUATED = "graduated"
    THESIS_PHASE = "thesis_phase"


class ApplicationStatus(enum.Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WAITLISTED = "waitlisted"


class StandingType(enum.Enum):
    GOOD_STANDING = "good_standing"
    WARNING = "warning"
    PROBATION = "probation"
    DISMISSED = "dismissed"


class ThesisStatus(enum.Enum):
    PROPOSAL_STAGE = "proposal_stage"
    ONGOING = "ongoing"
    SUBMITTED = "submitted"
    DEFENDED = "defended"
    COMPLETED = "completed"


class MilestoneType(enum.Enum):
    SUPERVISOR_ASSIGNED = "supervisor_assigned"
    PROPOSAL_DEFENSE = "proposal_defense"
    COMPREHENSIVE_EXAM = "comprehensive_exam"
    MID_TERM_EVALUATION = "mid_term_evaluation"
    FINAL_DEFENSE = "final_defense"
    PLAGIARISM_CLEARANCE = "plagiarism_clearance"


class MilestoneStatus(enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    FAILED = "failed"


class ClearanceStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    CLEARED = "cleared"
    BLOCKED = "blocked"


class DocumentType(enum.Enum):
    TRANSCRIPT = "transcript"
    ENROLLMENT_CERTIFICATE = "enrollment_certificate"
    DEGREE_CERTIFICATE = "degree_certificate"
    NO_OBJECTION_CERTIFICATE = "no_objection_certificate"
    RECOMMENDATION_LETTER = "recommendation_letter"
    FEE_STRUCTURE_LETTER = "fee_structure_letter"


class DocumentStatus(enum.Enum):
    REQUESTED = "requested"
    PROCESSING = "processing"
    READY_FOR_PICKUP = "ready_for_pickup"
    ISSUED = "issued"
    REJECTED = "rejected"


# --------------------------------------------------------------------------
# Module 2 core: Academics & University Life
# --------------------------------------------------------------------------

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False, unique=True)
    faculty_name = Column(String(120), nullable=False)  # e.g. "Faculty of Computing"
    head_of_department = Column(String(120))

    programs = relationship("Program", back_populates="department")
    faculty_members = relationship("Faculty", back_populates="department")
    courses = relationship("Course", back_populates="department")


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)          # e.g. "MS Computer Science"
    level = Column(Enum(ProgramLevel), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    duration_semesters = Column(Integer, nullable=False)  # MS=4, PhD=8 typical
    total_credit_hours = Column(Integer, nullable=False)
    requires_thesis = Column(Boolean, default=True)

    department = relationship("Department", back_populates="programs")
    students = relationship("Student", back_populates="program")
    applications = relationship("AdmissionApplication", back_populates="program")


class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(Integer, primary_key=True)
    sap_id = Column(String(10), unique=True, nullable=False)   # e.g. "F-10234"
    full_name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    designation = Column(String(60), nullable=False)  # Lecturer / Asst Prof / Assoc Prof / Prof
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    is_phd_supervisor = Column(Boolean, default=False)
    max_supervision_load = Column(Integer, default=5)
    joined_date = Column(Date, nullable=False)

    department = relationship("Department", back_populates="faculty_members")
    courses_taught = relationship("Course", back_populates="instructor")
    supervised_students = relationship("Student", back_populates="advisor")
    supervised_theses = relationship(
        "Thesis", back_populates="supervisor", foreign_keys="Thesis.supervisor_id"
    )


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True)
    label = Column(String(20), unique=True, nullable=False)  # e.g. "Fall 2025"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)

    enrollments = relationship("Enrollment", back_populates="semester")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)  # e.g. "CS-721"
    title = Column(String(150), nullable=False)
    credit_hours = Column(Integer, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("faculty.id"))
    program_level = Column(Enum(ProgramLevel), nullable=False)  # who it's meant for
    is_core = Column(Boolean, default=True)

    department = relationship("Department", back_populates="courses")
    instructor = relationship("Faculty", back_populates="courses_taught")
    enrollments = relationship("Enrollment", back_populates="course")


# --------------------------------------------------------------------------
# Student — hub entity linking most modules together
# --------------------------------------------------------------------------

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    sap_id = Column(String(10), unique=True, nullable=False)   # e.g. "55947"
    full_name = Column(String(120), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    advisor_id = Column(Integer, ForeignKey("faculty.id"))
    enrollment_date = Column(Date, nullable=False)
    current_semester = Column(Integer, default=1)
    cgpa = Column(Float, default=0.0)
    status = Column(Enum(StudentStatus), default=StudentStatus.ACTIVE)

    program = relationship("Program", back_populates="students")
    advisor = relationship("Faculty", back_populates="supervised_students")
    enrollments = relationship("Enrollment", back_populates="student")
    standings = relationship("AcademicStanding", back_populates="student")
    thesis = relationship("Thesis", back_populates="student", uselist=False)
    clearance = relationship("GraduationClearance", back_populates="student", uselist=False)
    document_requests = relationship("DocumentRequest", back_populates="student")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", "semester_id"),)

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    grade = Column(String(3))          # "A", "B+", "F", NULL if in progress
    grade_points = Column(Float)       # e.g. 4.0, 3.3

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    semester = relationship("Semester", back_populates="enrollments")


# --------------------------------------------------------------------------
# Module 3: Degree Progress & Academic Standing
# --------------------------------------------------------------------------

class AcademicStanding(Base):
    __tablename__ = "academic_standings"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=False)
    semester_gpa = Column(Float, nullable=False)
    cumulative_gpa = Column(Float, nullable=False)
    standing = Column(Enum(StandingType), nullable=False)
    credits_completed = Column(Integer, nullable=False)
    credits_remaining = Column(Integer, nullable=False)

    student = relationship("Student", back_populates="standings")


# --------------------------------------------------------------------------
# Module 1: Admissions & Program Exploration
# --------------------------------------------------------------------------

class AdmissionApplication(Base):
    __tablename__ = "admission_applications"

    id = Column(Integer, primary_key=True)
    applicant_name = Column(String(120), nullable=False)
    applicant_email = Column(String(150), nullable=False)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    applied_date = Column(Date, nullable=False)
    entry_test_score = Column(Float)
    previous_cgpa = Column(Float)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.SUBMITTED)
    decision_date = Column(Date)

    program = relationship("Program", back_populates="applications")


# --------------------------------------------------------------------------
# Module 4: Research & Thesis Journey (MS/PhD)
# --------------------------------------------------------------------------

class Thesis(Base):
    __tablename__ = "theses"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    title = Column(String(250), nullable=False)
    supervisor_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    co_supervisor_id = Column(Integer, ForeignKey("faculty.id"))
    status = Column(Enum(ThesisStatus), default=ThesisStatus.PROPOSAL_STAGE)
    proposal_date = Column(Date)
    defense_date = Column(Date)
    plagiarism_score = Column(Float)  # % similarity, HEC-style threshold checks

    student = relationship("Student", back_populates="thesis")
    supervisor = relationship("Faculty", back_populates="supervised_theses", foreign_keys=[supervisor_id])
    milestones = relationship("ThesisMilestone", back_populates="thesis")


class ThesisMilestone(Base):
    __tablename__ = "thesis_milestones"

    id = Column(Integer, primary_key=True)
    thesis_id = Column(Integer, ForeignKey("theses.id"), nullable=False)
    milestone_type = Column(Enum(MilestoneType), nullable=False)
    status = Column(Enum(MilestoneStatus), default=MilestoneStatus.PENDING)
    scheduled_date = Column(Date)
    completed_date = Column(Date)
    remarks = Column(Text)

    thesis = relationship("Thesis", back_populates="milestones")


# --------------------------------------------------------------------------
# Module 5: Degree Completion & Graduation
# --------------------------------------------------------------------------

class GraduationClearance(Base):
    __tablename__ = "graduation_clearances"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=False)
    thesis_submitted = Column(Boolean, default=False)
    no_dues_cleared = Column(Boolean, default=False)
    library_clearance = Column(Boolean, default=False)
    credits_requirement_met = Column(Boolean, default=False)
    status = Column(Enum(ClearanceStatus), default=ClearanceStatus.NOT_STARTED)
    convocation_batch = Column(String(30))  # e.g. "Spring 2027 Convocation"
    cleared_date = Column(Date)

    student = relationship("Student", back_populates="clearance")


# --------------------------------------------------------------------------
# Module 6: Forms & Documents
# --------------------------------------------------------------------------

class DocumentRequest(Base):
    __tablename__ = "document_requests"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    requested_date = Column(Date, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.REQUESTED)
    issued_date = Column(Date)

    student = relationship("Student", back_populates="document_requests")
