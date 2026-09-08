# Student Information Management System

A two-application monorepo implementing the backend REST API laboratory and its PyQt6
frontend integration laboratory.

```text
student-information-api/
├── backend/       Django REST Framework API, SQLite migrations/seed data, Swagger/tests
├── frontend/      PyQt6 desktop client, API service, role-aware screens/tests/evidence
├── setup.ps1      Creates the shared virtual environment and initializes both apps
└── run.ps1        Runs the backend and frontend together for local demonstration
```

The frontend communicates with the backend exclusively over HTTP. It has no database
driver, ORM import, schema, seed data, or replacement server. The backend remains the
authority for authentication, roles, validation, relationships, and academic rules.

## Quick start on Windows

```powershell
.\setup.ps1
.\run.ps1
```

`setup.ps1` installs pinned backend and frontend dependencies, creates ignored local
environment files, applies migrations and creates demonstration data. It preserves
existing environment files and seed records. Read `backend/.env` locally for the
generated `DEMO_PASSWORD`; sign in as `admin@demo.edu`.

If this checkout already contains `.venv`, `backend/.env`, and `backend/db.sqlite3`,
run only `run.ps1`. Closing the desktop application stops the helper backend process.

Manual development in separate terminals:

```powershell
.\.venv\Scripts\python backend\manage.py runserver 127.0.0.1:8000
.\.venv\Scripts\python frontend\app.py
```

Backend Swagger is available at http://127.0.0.1:8000/api/docs. The desktop client
shows its configured API URL on the login and profile screens.

## Verification

```powershell
.\.venv\Scripts\python backend\manage.py test academics
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python -m pytest frontend\tests -q
Remove-Item Env:QT_QPA_PLATFORM
```

The current verified result is 84 backend tests and 20 frontend tests. The frontend
suite includes a critical end-to-end flow against a temporary real backend and database.
See [backend documentation](backend/README.md), [frontend documentation](frontend/README.md),
and [frontend test evidence](frontend/docs/TEST_EVIDENCE.md).

## Distributable frontend

```powershell
.\frontend\scripts\build.ps1
```

The executable is created under `frontend/dist/StudentInformationSystem/`. The folder
is intentionally ignored because it is reproducible and large. Configure
`FRONTEND_API_BASE_URL` in `frontend/.env` when running from source. A packaged app reads
`.env` beside its executable and otherwise uses the documented local default.
