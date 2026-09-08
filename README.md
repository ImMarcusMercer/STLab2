# Student Information Management REST API

Backend laboratory project for the AI-Assisted Framework-Based REST API Development activity.
A secured, documented, and tested Student Information Management REST API built with
**Python / Django REST Framework** and **SQLite**.

## Technology Stack

| Layer         | Technology                                  |
|---------------|---------------------------------------------|
| Language      | Python 3.12+                                |
| Framework     | Django 5.2 + Django REST Framework          |
| Database      | SQLite (relational, migrations + seeders)   |
| Auth          | Token authentication (DB-backed, expiring)  |
| Validation    | DRF serializers + model constraints         |
| Filtering     | django-filter, SearchFilter, OrderingFilter |
| Docs          | drf-spectacular (OpenAPI/Swagger)           |
| Tests         | Django/DRF test client                      |

## Features

- Resource-oriented, versioned REST API under `/api/v1`
- Token authentication (`Authorization: Token <key>`) with configurable TTL
- Role-based authorization: `ADMIN`, `REGISTRAR`, `INSTRUCTOR`, `STUDENT`
- Object-level authorization (students only see their own records)
- CRUD for users, programs, students, courses, academic terms, course offerings,
  enrollments, and grades
- Domain endpoints: student enrollments, student grades, academic record, offering roster
- Consistent JSON error format and correct HTTP status codes (400/401/403/404/409/422/500/503)
- Strict server-side validation (unknown/read-only fields rejected)
- Search, filtering, sorting, and pagination on all collection endpoints
- OpenAPI schema at `/api/schema` and Swagger UI at `/api/docs`
- Seeder with realistic demo data (100 students, 200 enrollments, 100 grades, ...)
- Automated test suite covering authentication, CRUD, validation, authorization,
  enrollment, grades, and collections

## Prerequisites

- Python 3.12 or newer
- Git (optional, for versioned development history)
- An API client such as Postman, Insomnia, Bruno, or curl

## Installation

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the environment file
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux

# 4. Fill in .env (see Environment Configuration below)
```

## Environment Configuration

The project reads `config/settings.py` variables from a `.env` file; the real `.env` is
gitignored. Use `.env.example` as a template. Never commit your real `.env`.

| Variable            | Purpose                                             | Example                     |
|---------------------|-----------------------------------------------------|-----------------------------|
| `APP_ENV`           | `development` or `production`                       | `development`               |
| `DJANGO_SECRET_KEY` | Django secret; required, must not be the placeholder| long random string          |
| `DJANGO_DEBUG`      | Boolean debug flag                                  | `true` / `false`            |
| `ALLOWED_HOSTS`     | Comma-separated allowed hosts                       | `localhost,127.0.0.1`       |
| `DATABASE_NAME`     | SQLite file name                                    | `db.sqlite3`                |
| `TOKEN_TTL_HOURS`   | Token lifetime in hours                             | `24`                        |
| `DEMO_PASSWORD`     | Password for seeded demo accounts (12+ chars)       | change-me-2026!             |

Generate a secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Database Setup

```bash
# 1. Create/apply migrations
python manage.py migrate

# 2. Seed demonstration data (requires DEMO_PASSWORD or --password)
python manage.py seed_demo
# or: python manage.py seed_demo --password "SomeStrongPass2026!"
```

The seed command creates:

- 5+ users (1 admin, 1 registrar, 3 instructors, plus student accounts)
- 3 academic programs, 20 courses, 2 academic terms, 20 course offerings
- 100 students (60 linked to login accounts)
- 200 enrollments and 100 finalized grades

The seeder is idempotent: running it again skips records that already exist.

## Starting the API

```bash
python manage.py runserver
# -> http://127.0.0.1:8000
```

- OpenAPI schema: `GET /api/schema`
- Swagger UI documentation: `GET /api/docs` (recommended)
- Base path for all resources: `GET /api/v1/...`

## Authentication

1. Request a token:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@demo.edu", "password": "YOUR_DEMO_PASSWORD"}'
```

2. Send protected requests with the returned token:

```bash
curl http://127.0.0.1:8000/api/v1/students \
  -H "Authorization: Token <token>"
```

3. Endpoints: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`,
`GET /api/v1/auth/me`.

## Demo Accounts

Set `DEMO_PASSWORD` in `.env` before running `seed_demo`. All demo accounts share that
password.

| Role        | Email                     |
|-------------|---------------------------|
| Admin       | `admin@demo.edu`          |
| Registrar   | `registrar@demo.edu`      |
| Instructor  | `instructor1@demo.edu`    |
| Instructor  | `instructor2@demo.edu`    |
| Instructor  | `instructor3@demo.edu`    |
| Student     | `<first>.<last>.<n>@student.demo.edu` (e.g. via `GET /api/v1/users?role=STUDENT`) |

## API Documentation

- Interactive Swagger UI: `http://127.0.0.1:8000/api/docs`
- OpenAPI JSON schema: `http://127.0.0.1:8000/api/schema?format=json`
- Human-readable endpoint/role/error guide: `docs/API.md`
- Entity Relationship Diagram: `docs/ERD.md`
- Postman collection: `docs/student-information-api.postman_collection.json`

## Role Summary

| Role        | Minimum access                                                          |
|-------------|-------------------------------------------------------------------------|
| ADMIN       | Full system administration; all resources and user management.          |
| REGISTRAR   | Manage students, programs, courses, terms, offerings, enrollments, grades. |
| INSTRUCTOR  | View assigned offerings; view/grades only enrollments in own offerings. |
| STUDENT     | View only own profile, enrollments, grades, and academic record.        |

## Running Tests

```bash
python manage.py test academics
```

The suite covers the required areas (section 16 of the laboratory activity):
authentication (valid/invalid/missing), students (create/retrieve/update/duplicate/
invalid email/not found), authorization (admin permitted, student/instructor forbidden,
object-level access), enrollment (valid/invalid references/duplicate prevention),
grades (valid/invalid enrollment/unauthorized modification), and collections
(search/filter/sort/pagination).

## Project Layout

```
student-information-api/
├── academics/
│   ├── management/commands/seed_demo.py   # demo data generator
│   ├── migrations/                         # schema migrations
│   ├── api_support.py                      # pagination + error responses
│   ├── authentication.py                   # expiring token auth
│   ├── models.py                           # domain models and constraints
│   ├── schema.py                           # OpenAPI error-schema enrichment
│   ├── serializers.py                      # request/response serialization
│   ├── tests.py                            # automated test suite
│   ├── urls.py                             # /api/v1 routes
│   └── views.py                            # viewsets + permissions
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── docs/
│   ├── API.md
│   ├── ERD.md
│   └── student-information-api.postman_collection.json
├── .env.example
├── manage.py
└── requirements.txt
```

## AI-Assisted Development Notes

This project was developed with AI assistance following the laboratory's workflow
(Understand -> Plan -> Prompt -> Generate -> Review -> Test -> Improve -> Document).

- **Planning**: AI helped decompose the laboratory requirements into an ERD, endpoint
  list, and permission matrix.
- **Scaffolding**: Django project/configuration structure and the initial data models.
- **Code generation**: viewsets, serializers, permission classes, the seeder, and tests.
- **Review & test-driven fixes**: Every generated artifact was reviewed against Django/DRF
  conventions and validated by the automated test suite and manual `curl` requests.
  Examples of reviewed-and-corrected AI output include the router trailing-slash
  misconfiguration and the OpenAPI post-processing hook that originally inserted
  non-serializable objects into the schema.
- **No real credentials were exposed to AI tools.** The `.env` and `*.sqlite3` files are
  gitignored and excluded from any published repository.

All AI-generated code was reviewed, tested, and is explainable before acceptance into the
project, per section 3 of the laboratory policy.

## License

Academic project material for laboratory use.