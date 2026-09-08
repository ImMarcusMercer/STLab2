# Verification evidence

Verified on 2026-09-08 using Windows, Python 3.14, Django 5.2.17 and Django REST
Framework 3.18.1. Node.js 26.7.0 was used for the optional HTTP collection runner.

## Automated tests

Command: `python manage.py test academics --verbosity 2`

```text
Ran 84 tests in 41.986s
OK
System check identified no issues (0 silenced).
```

Full output: [test-results.txt](test-results.txt).

The suite includes authentication, student CRUD and validation, resource create/read/
PUT/PATCH/delete lifecycles, registrar and administrator permissions, student isolation,
instructor scope, grades, duplicate enrollment, occupied capacity, protected deletion,
filters, pagination, token renewal/revocation, seeder repeatability, safe errors and
OpenAPI response/example validation. One two-thread test races for a single seat and
asserts exactly one enrollment; the losing request cannot enroll on retry.

Expected error-path tests deliberately produce a sanitized RuntimeError log and may
produce a SQLite OperationalError log under contention. Those tests assert safe 500/503
responses and pass; they do not indicate unhandled test failures.

## Real HTTP acceptance collection

Started the application with:

```text
python manage.py runserver 127.0.0.1:8011 --noreload
python scripts/run_demo.py http://127.0.0.1:8011/api/v1
```

Result:

```text
Completed 54 HTTP requests and 56 assertions.
```

All requests matched their expected HTTP statuses. This run created accounts, a
program, student, course, term, offering, enrollment and grade; updated the grade as
its instructor; read the record as its student; rejected invalid/forbidden requests;
and checked logout revocation and protected deletion. The test server was stopped
afterward. Demonstration records remain in the local database.

## Clean database reproduction

Command: `python scripts/verify_rebuild.py`

The script created a separate temporary SQLite database, applied all migrations,
seeded twice, checked exact counts and ran model validation on every seeded record:

```text
User: 65
Program: 3
Student: 100
Course: 20
AcademicTerm: 2
CourseOffering: 20
Enrollment: 200
Grade: 100
PASS clean database rebuild, unchanged seed counts, and validation of all seeded records
```

The temporary database was removed by the script's scoped TemporaryDirectory cleanup.
The user's original local database was preserved.

## Other checks

| Command | Result |
|---|---|
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py spectacular --file docs/openapi.yaml --validate --fail-on-warn` | Exit 0, no warnings/errors |
| `python -m pip check` | No broken requirements |

These results establish the tested behavior in this environment. Production load,
external database engines and the student's ability to explain/modify the code were
not assessed by these automated checks.
