# PyQt6 Student Information System frontend

This is a desktop frontend for the existing Django REST API in `../backend`. It uses
PyQt6 as the client UI framework and `requests` in background Qt workers. All lists,
forms, identities and academic records come from HTTP endpoints; the frontend never
opens the backend database.

## Run

From the repository root after `setup.ps1`:

```powershell
.\.venv\Scripts\python frontend\app.py
```

Or use `run.ps1` to start both applications. Configure the connection in `.env`:

```dotenv
FRONTEND_API_BASE_URL=http://127.0.0.1:8000/api/v1
FRONTEND_REQUEST_TIMEOUT_SECONDS=15
```

Copy `.env.example` to `.env`, or run `python frontend/scripts/setup_local.py`. No
password, token, signing key, or database credential belongs in this file.

## Features

- Public login with real backend feedback; authenticated shell and logout revocation.
- Role-aware navigation for administrator, registrar, instructor, and student users.
- Live dashboard counts and profile/API connection details.
- Students list with backend search, program/year/status filters, sorting and pagination.
- Authorized create/edit/deactivate with client checks and mapped backend field errors.
- Programs, courses, terms, offerings, enrollments and grades in reusable list/form pages.
- Relationship selectors populated from API resources instead of hardcoded records.
- Readable academic record grouped by term from the aggregate endpoint.
- Explicit empty, busy, forbidden, not-found, conflict, validation, server and network states.
- Confirmation before logout, deletion, or student deactivation.
- Narrow-window layout adjustments and keyboard-accessible labeled controls.

UI visibility is a usability feature. Every protected action is still sent to the
backend, which makes the actual authorization decision.

## Tests

```powershell
$env:QT_QPA_PLATFORM='offscreen'
..\.venv\Scripts\python -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM
```

The tests cover the API client, token lifecycle, normalized HTTP/network errors, form
validation mapping, collection rendering, query controls, protected navigation,
role menus, narrow layout, and a real API flow using a disposable migrated/seeded
backend database. See [test evidence](docs/TEST_EVIDENCE.md).

## Build

```powershell
.\scripts\build.ps1
```

The PyInstaller spec creates `dist/StudentInformationSystem/StudentInformationSystem.exe`.
Keep `.env` outside version control and point the packaged client to a reachable API.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API integration map](docs/API_INTEGRATION_MAP.md)
- [AI development log](docs/AI_DEVELOPMENT_LOG.md)
- [Demonstration guide](docs/DEMONSTRATION.md)
- [Screenshot evidence](docs/SCREENSHOTS.md)
- [Test evidence](docs/TEST_EVIDENCE.md)
