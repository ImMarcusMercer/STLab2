# Student Information Management REST API

Backend-only implementation of `AI_Assisted_REST_API_Laboratory_Activity.pdf`.
Built with Django 5.2, Django REST Framework, SQLite, django-filter and drf-spectacular.
It covers users/roles, students, programs, courses, academic terms, course offerings,
enrollments, grades and academic records. No graphical frontend is required.

## Start the existing local project

From this directory in PowerShell:

```powershell
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

Open **http://127.0.0.1:8000/api/docs**. The local `.env` and seeded `db.sqlite3`
are already configured. Use `admin@demo.edu` and the `DEMO_PASSWORD` in your local
`.env` to log in. These local files are excluded from Git.

## Install on another machine

Prerequisites: Python 3.12+ with pip, Git, and optionally Postman. The project was
verified on Windows with Python 3.14. Dependencies are pinned in `requirements.txt`.

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/setup_local.py
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/setup_local.py
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

`setup_local.py` generates a random Django secret and local demo password from
`.env.example`. It never overwrites an existing `.env`. Alternatively, copy the example
yourself and configure it. Read the generated `.env` locally for the demo password.

## Configuration and database

| Variable | Meaning |
|---|---|
| `APP_ENV` | `development` by default; `production` enables HTTPS security settings and disables demo seeding |
| `DJANGO_SECRET_KEY` | Required random secret; placeholder is rejected |
| `DJANGO_DEBUG` | Defaults to `false` so tracebacks stay out of responses |
| `ALLOWED_HOSTS` | Comma-separated hostnames; localhost/127.0.0.1 for local use |
| `DATABASE_NAME` | SQLite file path, relative to the project unless absolute |
| `TOKEN_TTL_HOURS` | Token lifetime; default 24 hours |
| `DEMO_PASSWORD` | Local seed-account password, at least 12 characters and subject to password validation |

`python manage.py migrate` recreates the schema from versioned migrations. Run
`python manage.py makemigrations` after an intentional model change, review the
migration, then apply it. SQLite enables foreign keys and uses IMMEDIATE transactions
for API writes so seat validation and insertion happen atomically.

The repeatable `seed_demo` command creates at least:

| Users | Programs | Students | Courses | Terms | Offerings | Enrollments | Grades |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 65 | 3 | 100 | 20 | 2 | 20 | 200 | 100 |

Sixty students have linked login accounts. Running the command again retains existing
records and passwords. It repairs whitespace in legacy generated demo email addresses.
Extra records created during a demonstration are retained.

## Authentication and demonstration accounts

| Role | Email |
|---|---|
| Administrator | `admin@demo.edu` |
| Registrar | `registrar@demo.edu` |
| Instructors | `instructor1@demo.edu`, `instructor2@demo.edu`, `instructor3@demo.edu` |
| Students | Query `/api/v1/users?role=STUDENT` as admin to find seeded addresses |

All newly seeded users use your configured `DEMO_PASSWORD`. The public collection
contains no populated passwords or tokens.

1. POST `/api/v1/auth/login` with JSON `{"email":"admin@demo.edu","password":"YOUR_LOCAL_PASSWORD"}`.
2. Copy `data.token` and send `Authorization: Token <token>` with protected requests.
3. GET `/api/v1/auth/me` returns the current user.
4. POST `/api/v1/auth/logout` returns 204 and invalidates the token.

In Swagger, use **Authorize** and enter `Token ` followed by the token. An expired token
returns 401; login issues a replacement. Password changes and account deactivation
invalidate tokens. Login is limited to 10 attempts per minute per IP in a single process.

## Authorization and API behavior

Administrators manage all resources and account links. Registrars manage academic
resources but cannot administer users or reassign account ownership. Instructors read
only assigned offerings, their rosters and enrollments, and create/update grades for
those offerings. Full student profiles and transcripts are restricted to staff and the
student concerned. Students have read-only access to their own private records.
All authenticated roles can read the academic catalog.

CRUD responses follow DRF conventions: individual resource objects, paginated lists,
and empty 204 responses for successful deletion. Login, current-user and academic-record
responses have a documented success envelope. All API errors share the same
`success/message/errors` envelope. Validation uses 422, hidden records use 404, and
protected deletion/constraint conflicts use 409.

Use `search`, `sort` (e.g. `-last_name`), `page` and `per_page` on main collections.
Student filters include `program_id`, `year_level` and `status`. Nested collections
are also paginated. Page size defaults to 20 and is capped at 100. Academic records
page enrollment rows before grouping by term; follow `data.pagination.next` to obtain
all pages. Grades range from 0 to 100; finalization requires a final grade.

## Documentation and API client

- [API guide](docs/API.md): endpoints, role rules, filters, responses and errors.
- [OpenAPI schema](docs/openapi.yaml): complete machine-readable contract.
- Swagger UI: `/api/docs`; live schema: `/api/schema?format=json`.
- [ERD](docs/ERD.md): normalized entities, keys and relationships.
- [Architecture and AI notes](docs/ARCHITECTURE.md): design decisions and review responsibilities.
- [Postman collection](docs/student-information-api.postman_collection.json): 54 requests covering positive and negative acceptance cases.
- [Demonstration checklist](docs/DEMONSTRATION.md): maps the PDF's mandatory cases to executable requests.
- [Test evidence](docs/TEST_EVIDENCE.md): verification commands and results.

Import the Postman collection, set its `demo_password` variable to your local password,
and run the folders in order. It captures IDs and role tokens automatically, creates
fresh demonstration resources, and checks expected status codes. It adds records to
the database; use a separate local database if you want to keep the original seed set.
Rebuild the collection after editing its source with `python scripts/build_collection.py`.

## Tests and checks

With the virtual environment activated, or using its Python executable:

```bash
python manage.py test academics --verbosity 2
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file docs/openapi.yaml --validate --fail-on-warn
```

Tests create and destroy a separate test database. They cover authentication,
student CRUD, all roles, object isolation, validation, filters, pagination, enrollment
capacity (including concurrent requests), grade authorization, referential integrity,
error redaction, token renewal and repeatable seeding. The HTTP demonstration runner
in `scripts/run_demo.py` exercises the collection against a running server.

## Project structure

```text
academics/models.py                   Domain schema and database constraints
academics/migrations/                Versioned schema
academics/serializers.py              Validation and public fields
academics/views.py                    API actions, authorization, transactions
academics/filters.py                  Filtering and stable allowlisted sorting
academics/authentication.py           Expiring token authentication
academics/api_support.py              Pagination and safe errors
academics/schema.py                   OpenAPI examples and error contracts
academics/management/commands/        Demo seeder
academics/tests.py, test_*.py          Automated tests
config/                              Settings, routing, WSGI
scripts/                             Local setup and acceptance client tooling
docs/                                Submission documentation and API collection
```

## AI accountability

AI contributed requirements analysis, schema and API code, seed data, tests and
documentation. The continuation review identified and corrected access-control leaks,
missing pagination, ignored filters, stale-token login, and seeder defects. Automated
verification is recorded in `docs/TEST_EVIDENCE.md`. The student must still read the
code, explain these decisions and demonstrate a modification; automated checks do not
establish the student's understanding. Local Git commits record actual development
stages and are attributed to Codex where created by this assistant.

This is a local laboratory application. Deployment needs a production WSGI server,
TLS, database backups and an appropriately shared throttle store; Django's development
server and its default in-memory throttle cache are intended for local use.
