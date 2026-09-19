"""
seed.py — populate the mock institutional DB with realistic, fully synthetic data.

Run:  python seed.py            (creates twin_mock.db, a SQLite file, in this folder)
      python seed.py --reset    (drops & recreates all tables first)

Nothing here is copied from or derived from any real student, faculty member,
or institutional record — every name, ID, score and date is Faker-generated
or randomly sampled from realistic distributions.
"""

import argparse
import random
from datetime import date, timedelta

from faker import Faker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base, Department, Program, Faculty, Semester, Course, Student, Enrollment,
    AcademicStanding, AdmissionApplication, Thesis, ThesisMilestone,
    GraduationClearance, DocumentRequest,
    ProgramLevel, StudentStatus, ApplicationStatus, StandingType, ThesisStatus,
    MilestoneType, MilestoneStatus, ClearanceStatus, DocumentType, DocumentStatus,
)

fake = Faker()
random.seed(42)
Faker.seed(42)

DB_PATH = "sqlite:///twin_mock.db"

# --------------------------------------------------------------------------
# Config — tune these to change dataset size
# --------------------------------------------------------------------------
N_STUDENTS = 500
N_FACULTY = 40
MS_PHD_SPLIT = 0.75   # 75% MS/MPhil, 25% PhD — realistic for most CS depts

DEPARTMENTS = [
    ("Department of Computer Science", "Faculty of Computing", ["MS Computer Science", "PhD Computer Science"]),
    ("Department of Software Engineering", "Faculty of Computing", ["MS Software Engineering"]),
    ("Department of Cybersecurity", "Faculty of Computing", ["MS Cybersecurity", "PhD Cybersecurity"]),
    ("Department of Data Science", "Faculty of Computing", ["MS Data Science"]),
]

COURSE_TITLES = [
    "Advanced Algorithms", "Distributed Systems", "Machine Learning",
    "Applied Cryptography", "Software Architecture", "Research Methodology",
    "Advanced Database Systems", "Natural Language Processing",
    "Cloud Computing", "Formal Methods", "Computer Vision",
    "Network Security", "Big Data Analytics", "Human-Computer Interaction",
]

DESIGNATIONS = ["Lecturer", "Assistant Professor", "Associate Professor", "Professor"]


def weighted_grade():
    """Return (letter, points) sampled from a realistic bell-curve, not uniform."""
    r = random.random()
    if r < 0.35:
        return "A", 4.0
    if r < 0.60:
        return "A-", 3.7
    if r < 0.80:
        return "B+", 3.3
    if r < 0.92:
        return "B", 3.0
    if r < 0.97:
        return "B-", 2.7
    if r < 0.995:
        return "C+", 2.3
    return "F", 0.0


def build(session):
    # ---- Departments & Programs ----
    departments, programs = [], []
    for name, faculty_name, program_names in DEPARTMENTS:
        dept = Department(
            name=name, faculty_name=faculty_name,
            head_of_department=fake.name(),
        )
        session.add(dept)
        session.flush()
        departments.append(dept)
        for pname in program_names:
            level = ProgramLevel.PHD if "PhD" in pname else ProgramLevel.MS
            prog = Program(
                name=pname, level=level, department_id=dept.id,
                duration_semesters=8 if level == ProgramLevel.PHD else 4,
                total_credit_hours=54 if level == ProgramLevel.PHD else 30,
                requires_thesis=True,
            )
            session.add(prog)
            programs.append(prog)
    session.flush()

    # ---- Faculty ----
    faculty_list = []
    for i in range(N_FACULTY):
        dept = random.choice(departments)
        f = Faculty(
            sap_id=f"F-{10000 + i}",
            full_name=fake.name(),
            email=fake.unique.email(),
            designation=random.choices(DESIGNATIONS, weights=[0.15, 0.4, 0.3, 0.15])[0],
            department_id=dept.id,
            is_phd_supervisor=random.random() < 0.5,
            max_supervision_load=random.randint(3, 8),
            joined_date=fake.date_between(start_date="-15y", end_date="-1y"),
        )
        session.add(f)
        faculty_list.append(f)
    session.flush()
    supervisors = [f for f in faculty_list if f.is_phd_supervisor]

    # ---- Semesters (last 4 years, Fall/Spring) ----
    semesters = []
    year = date.today().year - 4
    for y in range(year, date.today().year + 1):
        for term, (m_start, m_end) in [("Spring", (2, 6)), ("Fall", (9, 1))]:
            label = f"{term} {y}"
            sem = Semester(
                label=label,
                start_date=date(y, m_start, 1),
                end_date=date(y if m_end != 1 else y + 1, m_end, 28),
                is_current=(y == date.today().year and term == "Fall"),
            )
            session.add(sem)
            semesters.append(sem)
    session.flush()

    # ---- Courses ----
    courses = []
    for d_idx, dept in enumerate(departments):
        for i, title in enumerate(random.sample(COURSE_TITLES, k=6)):
            level = random.choice(list(ProgramLevel))
            c = Course(
                code=f"D{d_idx}-{700 + i}",
                title=title,
                credit_hours=3,
                department_id=dept.id,
                instructor_id=random.choice(
                    [f.id for f in faculty_list if f.department_id == dept.id]
                ),
                program_level=level,
                is_core=random.random() < 0.6,
            )
            session.add(c)
            courses.append(c)
    session.flush()

    # ---- Students (+ enrollments, standing, thesis, clearance, docs) ----
    for i in range(N_STUDENTS):
        program = random.choices(
            programs,
            weights=[3 if p.level != ProgramLevel.PHD else 1 for p in programs],
        )[0]
        is_phd = program.level == ProgramLevel.PHD
        enroll_date = fake.date_between(start_date="-4y", end_date="-1m")
        semesters_elapsed = min(
            program.duration_semesters,
            max(1, (date.today() - enroll_date).days // 180),
        )

        status = random.choices(
            [StudentStatus.ACTIVE, StudentStatus.ON_PROBATION,
             StudentStatus.WITHDRAWN, StudentStatus.GRADUATED, StudentStatus.THESIS_PHASE],
            weights=[0.55, 0.08, 0.05, 0.17, 0.15],
        )[0]

        advisor = random.choice(supervisors) if supervisors else random.choice(faculty_list)

        student = Student(
            sap_id=str(55000 + i),
            full_name=fake.name(),
            email=fake.unique.email(),
            program_id=program.id,
            advisor_id=advisor.id,
            enrollment_date=enroll_date,
            current_semester=semesters_elapsed,
            status=status,
        )
        session.add(student)
        session.flush()

        # Enrollments across elapsed semesters + running GPA
        dept_courses = [c for c in courses if c.department_id == program.department_id]
        total_points, total_courses = 0.0, 0
        for sem_idx in range(min(semesters_elapsed, len(semesters))):
            sem = semesters[-(sem_idx + 1)]
            for course in random.sample(dept_courses, k=min(2, len(dept_courses))):
                letter, points = weighted_grade()
                session.add(Enrollment(
                    student_id=student.id, course_id=course.id, semester_id=sem.id,
                    grade=letter, grade_points=points,
                ))
                total_points += points
                total_courses += 1

            if total_courses:
                cgpa = round(total_points / total_courses, 2)
                standing = (
                    StandingType.PROBATION if cgpa < 2.5 else
                    StandingType.WARNING if cgpa < 2.8 else
                    StandingType.GOOD_STANDING
                )
                session.add(AcademicStanding(
                    student_id=student.id, semester_id=sem.id,
                    semester_gpa=round(random.uniform(max(0, cgpa - 0.5), min(4.0, cgpa + 0.5)), 2),
                    cumulative_gpa=cgpa,
                    standing=standing,
                    credits_completed=total_courses * 3,
                    credits_remaining=max(0, program.total_credit_hours - total_courses * 3),
                ))
                student.cgpa = cgpa

        # Thesis journey — required once past coursework phase
        needs_thesis = status in (StudentStatus.THESIS_PHASE, StudentStatus.GRADUATED)
        if needs_thesis or (is_phd and semesters_elapsed > 2):
            thesis_status = (
                ThesisStatus.COMPLETED if status == StudentStatus.GRADUATED else
                random.choice([ThesisStatus.PROPOSAL_STAGE, ThesisStatus.ONGOING, ThesisStatus.SUBMITTED])
            )
            thesis_kind = random.choice(["Framework", "Study", "Approach", "System"])
            thesis_title = f"{fake.catch_phrase()}: A {thesis_kind} for {fake.bs()}"
            thesis = Thesis(
                student_id=student.id,
                title=thesis_title,
                supervisor_id=advisor.id,
                status=thesis_status,
                proposal_date=enroll_date + timedelta(days=365),
                defense_date=enroll_date + timedelta(days=700) if thesis_status in (
                    ThesisStatus.SUBMITTED, ThesisStatus.COMPLETED) else None,
                plagiarism_score=round(random.uniform(3, 19), 1),
            )
            session.add(thesis)
            session.flush()

            for m_type in [MilestoneType.SUPERVISOR_ASSIGNED, MilestoneType.PROPOSAL_DEFENSE,
                           MilestoneType.MID_TERM_EVALUATION, MilestoneType.FINAL_DEFENSE]:
                done = (thesis_status == ThesisStatus.COMPLETED) or (
                    thesis_status == ThesisStatus.ONGOING and m_type != MilestoneType.FINAL_DEFENSE
                )
                session.add(ThesisMilestone(
                    thesis_id=thesis.id,
                    milestone_type=m_type,
                    status=MilestoneStatus.COMPLETED if done else MilestoneStatus.PENDING,
                    scheduled_date=enroll_date + timedelta(days=random.randint(100, 800)),
                    completed_date=enroll_date + timedelta(days=random.randint(100, 800)) if done else None,
                ))

        # Graduation clearance for graduated students
        if status == StudentStatus.GRADUATED:
            session.add(GraduationClearance(
                student_id=student.id,
                thesis_submitted=True, no_dues_cleared=True,
                library_clearance=True, credits_requirement_met=True,
                status=ClearanceStatus.CLEARED,
                convocation_batch=f"{random.choice(['Spring', 'Fall'])} {random.randint(2023, 2026)} Convocation",
                cleared_date=enroll_date + timedelta(days=800),
            ))

        # A handful of document requests per student
        for _ in range(random.randint(0, 3)):
            doc_type = random.choice(list(DocumentType))
            req_date = fake.date_between(start_date=enroll_date, end_date="today")
            issued = random.random() < 0.8
            session.add(DocumentRequest(
                student_id=student.id, document_type=doc_type,
                requested_date=req_date,
                status=DocumentStatus.ISSUED if issued else DocumentStatus.PROCESSING,
                issued_date=req_date + timedelta(days=random.randint(1, 10)) if issued else None,
            ))

    # ---- Admission applications (pipeline feeding future students) ----
    for _ in range(150):
        program = random.choice(programs)
        applied = fake.date_between(start_date="-6m", end_date="today")
        status = random.choices(
            list(ApplicationStatus), weights=[0.15, 0.25, 0.3, 0.2, 0.1]
        )[0]
        session.add(AdmissionApplication(
            applicant_name=fake.name(),
            applicant_email=fake.unique.email(),
            program_id=program.id,
            applied_date=applied,
            entry_test_score=round(random.uniform(50, 98), 1),
            previous_cgpa=round(random.uniform(2.5, 4.0), 2),
            status=status,
            decision_date=applied + timedelta(days=random.randint(7, 30))
            if status != ApplicationStatus.SUBMITTED else None,
        ))

    session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop & recreate all tables first")
    args = parser.parse_args()

    engine = create_engine(DB_PATH)
    if args.reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()
    build(session)
    session.close()

    print(f"Seeded {DB_PATH} — {N_STUDENTS} students, {N_FACULTY} faculty, "
          f"{len(DEPARTMENTS)} departments, 150 admission applications.")


if __name__ == "__main__":
    main()
