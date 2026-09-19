# Module Ownership & API Contracts

Fill this in as a team so everyone knows who owns what and what data each
module expects/produces. This doubles as your integration reference — update
it whenever a model or endpoint shape changes.

| # | Module | Owner | Backend model(s) | Depends on |
|---|--------|-------|-------------------|------------|
| 1 | Admissions & Program Exploration | | `AdmissionApplication`, `Program` | — |
| 2 | Academics & University Life | | `Course`, `Enrollment`, `Faculty`, UniTime `Class_`/`Assignment` | Module 3 (GPA feeds standing) |
| 3 | Degree Progress & Academic Standing | | `AcademicStanding` | Module 2 (enrollment/grades) |
| 4 | Research & Thesis Journey | | `Thesis`, `ThesisMilestone` | Module 2 (advisor assignment) |
| 5 | Degree Completion & Graduation | | `GraduationClearance` | Modules 3 & 4 (standing + thesis complete) |
| 6 | Forms & Documents | | `DocumentRequest` | Module 1 & 5 (varies by doc type) |

## Meeting notes
Keep a running log here or link to a shared Google Doc/Notion page. Suggested
format per entry: date, attendees, decisions made, action items.

## API contract changes
Before changing a shared model's fields (especially in `mock_data/models.py`
or `unitime_models.py`), post here or in the team chat what's changing and
why — those files are shared infrastructure and a silent change breaks every
module that reads from them.
