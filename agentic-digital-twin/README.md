# AI Agentic Digital Twin for Program Coordination

Final Year Project — Riphah International University, Faculty of Computing
Supervised under RISE (Director: Dr. Naveed Ikram)

A self-service mobile app for Graduate & Postgraduate Computing students,
built as a multi-agent digital twin integrating (mocked) CMS/SAP, UniTime,
and LMS data.

## Team
| Name | SAP ID | Modules owned |
|------|--------|----------------|
| Almeerah Firdouse | 55947 | _fill in_ |
| Saira Kousar | 55503 | _fill in_ |
| Aliza Shahid | 56264 | _fill in_ |

## Modules (see `docs/module-ownership.md` for detail)
1. Admissions & Program Exploration
2. Academics & University Life
3. Degree Progress & Academic Standing
4. Research & Thesis Journey
5. Degree Completion & Graduation
6. Forms & Documents

Timetabling/class scheduling and fee challans/financial clearance are
explicitly **out of scope** — scheduling data is only consumed (from the
mock UniTime-shaped DB) for display, not built or optimized by this app.

## Repo layout
```
agentic-digital-twin/
├── backend/
│   ├── app/
│   │   ├── models/       # one file per module — ORM models for app-level logic
│   │   └── mock_data/    # mock CMS/SAP + UniTime DB schema & seed scripts
│   ├── tests/
│   └── requirements.txt
├── mobile/                # self-service mobile app (Flutter/React Native — TBD)
├── docs/                  # module ownership, API contracts, meeting notes
└── .github/workflows/     # CI checks on every PR
```

## Getting started
```bash
git clone <repo-url>
cd agentic-digital-twin/backend
python -m venv venv && source venv/bin/activate     # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Build the mock databases (see backend/app/mock_data/README.md for detail)
cd app/mock_data
python seed.py --reset
python unitime_seed.py --reset
```

## Contributing
See `CONTRIBUTING.md` for the branching model, commit conventions, and PR process.
Every module lives behind its own `feature/<module-name>` branch — never
commit directly to `main` or `dev`.
