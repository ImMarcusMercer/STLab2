# Frontend test and build evidence

Verified on 2026-09-08 using Windows 11, Python 3.14.7, PyQt6 6.11.0,
requests 2.34.2, pytest 9.1.1, and pytest-qt 4.5.0.

## Automated frontend tests

Command from `frontend/`:

```powershell
$env:QT_QPA_PLATFORM='offscreen'
..\.venv\Scripts\python -m pytest -q
```

Coverage includes:

- successful token login/auth header and empty 204 logout;
- invalid session clearing and normalized 403/404/409/422/500/network failures;
- client-required/email validation and backend field-error mapping;
- loading indicator, API-driven table/pagination, filters and query parameters;
- protected navigation, not-found route, four-role menu visibility and narrow layout;
- a critical end-to-end flow using the real Django application and a temporary SQLite
  database: migrate, seed, login, list/search/filter, create/read/edit student, duplicate
  validation, student-role 403, logout.

Full current console output is saved in [test-results.txt](test-results.txt). The E2E
fixture selects a free localhost port, suppresses credentials and server output, stops
the temporary server, and lets `TemporaryDirectory` remove only its disposable database.

## Backend regression after reorganization

Command from the repository root:

```powershell
.\.venv\Scripts\python backend\manage.py test academics
```

Result: `Ran 84 tests ... OK`. This confirms moving Django under `backend/` did not
break migrations, endpoints, security rules, schema contracts, seeding, or concurrency.

## Real UI evidence

`scripts/capture_screenshots.py` logged in through the live REST API and captured six
rendered PyQt windows. It shows invalid login, admin dashboard, students, offerings,
a student's graded academic record at 800x600, and an unreachable-backend retry state.
Images and context are in [SCREENSHOTS.md](SCREENSHOTS.md).

## Distributable build

Command: `python -m PyInstaller --noconfirm --clean student-information-system.spec`

Result: build completed successfully in `frontend/dist/StudentInformationSystem`.
`StudentInformationSystem.exe` was started with Qt's offscreen platform, remained alive
for a three-second smoke check, and was then stopped. Missing-module analysis contained
only optional or non-Windows modules from Python, setuptools, requests, and urllib3.
The reproducible `dist/` output is ignored; the versioned spec and build script are the
submission artifact.

## Dependency and source checks

Both applications compile with `python -m compileall -q frontend backend`. Django
reports no system-check issues and no missing migrations. `pip check` reports no broken
requirements. Git's whitespace check reports no source errors.

These checks verify this machine and current dependency set. They do not test every
screen reader, operating system, high-DPI setting, intermittent network, or production
deployment topology. The student's live explanation and requested modification remain
part of the laboratory assessment.
