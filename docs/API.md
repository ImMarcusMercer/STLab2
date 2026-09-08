# API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

Interactive documentation: `GET /api/docs` (Swagger UI) · Schema: `GET /api/schema`

## Authentication

All protected endpoints require the header:

```
Authorization: Token <token>
```

| Method | Path              | Auth | Description                                  |
|--------|-------------------|------|----------------------------------------------|
| POST   | `/auth/login`     | None | Login; returns `token`, `expires_at`, `user` |
| POST   | `/auth/logout`    | Yes  | Deletes the current token (204)              |
| GET    | `/auth/me`        | Yes  | Returns the current authenticated user       |

### Login request

```json
{ "email": "admin@demo.edu", "password": "your-password" }
```

### Login response (200)

```json
{
  "success": true,
  "message": "Login successful.",
  "data": {
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
    "expires_at": "2026-09-09T00:00:00Z",
    "user": { "id": 1, "name": "Admin User", "email": "admin@demo.edu",
              "role": "ADMIN", "is_active": true, "created_at": "..." }
  }
}
```

Token expiry is controlled by `TOKEN_TTL_HOURS` (default 24). Expired tokens are deleted
and rejected with 401.

## Response Format

Standard CRUD responses use DRF conventions (the serialized object directly, or a
paginated result object for lists). Failed requests use a consistent envelope:

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "email": ["A valid email address is required."]
  }
}
```

Domain/action endpoints (`auth/*`, `/students/{id}/enrollments`,
`/students/{id}/grades`, `/students/{id}/academic-record`,
`/course-offerings/{id}/students`) use a success envelope:

```json
{
  "success": true,
  "message": "Enrollments retrieved.",
  "data": [ ... ]
}
```

## HTTP Status Codes

| Code | Use                                                                 |
|------|---------------------------------------------------------------------|
| 200  | Successful retrieval/update with body                               |
| 201  | Resource created                                                    |
| 204  | Successful operation, no body (logout)                              |
| 400  | Malformed request                                                   |
| 401  | Missing or invalid authentication                                   |
| 403  | Authenticated but not permitted                                     |
| 404  | Resource not found                                                  |
| 409  | Duplicate/conflicting state or protected resource conflict          |
| 422  | Request validation failed                                           |
| 500  | Internal server error (no internals leaked)                         |
| 503  | Database temporarily unavailable                                    |

## Role / Permission Rules

| Resource        | ADMIN | REGISTRAR | INSTRUCTOR                    | STUDENT            |
|-----------------|:-----:|:---------:|-------------------------------|--------------------|
| `/users`        |  CRUD | –         | –                             | –                  |
| `/programs`     |  CRUD | CRUD      | read                          | read               |
| `/courses`      |  CRUD | CRUD      | read                          | read               |
| `/academic-terms`| CRUD | CRUD      | read                          | read               |
| `/course-offerings`| CRUD| CRUD     | read (own only)               | read               |
| `/enrollments`  |  CRUD | CRUD      | read (own offerings only)     | read (own only)    |
| `/grades`       | CRUD  | CRUD      | create/update (own offerings only) | read (own only) |
| `/students`     |  CRUD | CRUD      | read (enrolled students)      | read (own only)    |

Object-level rules are enforced on the server:
- A `STUDENT` requesting another student's profile, enrollments, grades, or academic
  record receives `404` (the resource is filtered out of the query set).
- An `INSTRUCTOR` grading an enrollment outside their offerings receives `403`.
- Admin cannot demote or deactivate themselves.

## Students

| Method | Path                          | Description                                |
|--------|-------------------------------|--------------------------------------------|
| GET    | `/students`                   | List (search/filter/sort/paginate)         |
| POST   | `/students`                   | Create student                             |
| GET    | `/students/{id}`              | Retrieve student                           |
| PUT    | `/students/{id}`              | Replace student                            |
| PATCH  | `/students/{id}`              | Partial update                             |
| DELETE | `/students/{id}`              | Delete/deactivate? (use status=INACTIVE)   |
| GET    | `/students/{id}/enrollments`  | Student enrollments                        |
| GET    | `/students/{id}/grades`       | Student grades                             |
| GET    | `/students/{id}/academic-record` | Aggregated record grouped by term       |

Duplicating `student_number` returns 422. Referencing a non-existent `program_id` returns
422.

## Programs

`GET/POST /programs`, `GET/PUT/PATCH/DELETE /programs/{id}`

Fields: `code` (unique), `name`, `description`, `status` (`ACTIVE`/`INACTIVE`).

## Courses

`GET/POST /courses`, `GET/PUT/PATCH/DELETE /courses/{id}`

Fields: `course_code` (unique), `course_title`, `description`, `units` (0.5–12),
`status`.

## Academic Terms

`GET/POST /academic-terms`, `GET/PUT/PATCH/DELETE /academic-terms/{id}`

Fields: `academic_year` (`YYYY-YYYY`, consecutive), `semester`
(`FIRST`/`SECOND`/`SUMMER`), `start_date`, `end_date`, `status`. End date must be on or
after start date.

## Course Offerings

`GET/POST /course-offerings`, `GET/PUT/PATCH/DELETE /course-offerings/{id}`,
`GET /course-offerings/{id}/students`

Fields: `course_id`, `academic_term_id`, `instructor_id` (instructor users only),
`section`, `schedule`, `room`, `capacity` (1–1000), `status`. Course+term+section must be
unique; capacity cannot drop below occupied seats; course/term cannot change after
enrollment.

Enrolled students roster (`/course-offerings/{id}/students`) is restricted: students are
denied (403).

## Enrollments

`GET/POST /enrollments`, `GET/PATCH/DELETE /enrollments/{id}`

Fields: `student_id`, `course_offering_id`, `enrollment_date` (auto), `status`
(`ENROLLED`/`DROPPED`/`COMPLETED`).

Rules:
- Duplicate student+offering is prevented (422 / 409).
- Student, offering, and term must be `ACTIVE`; offering must have an open seat.
- Enrollment links cannot be changed; a graded enrollment cannot be dropped.

## Grades

`GET/POST /grades`, `GET/PUT/PATCH /grades/{id}` (no DELETE)

Fields: `enrollment_id`, `midterm_grade`, `final_grade` (0–100), `remarks`, `status`
(`DRAFT`/`FINALIZED`).

Rules:
- Instructors may only grade enrollments in their assigned offerings (403 otherwise).
- Dropped enrollments cannot be graded.
- A `FINALIZED` grade requires `final_grade`.

## Search, Filtering, Sorting, Pagination

Available on every collection endpoint.

| Feature   | Example                                                    |
|-----------|------------------------------------------------------------|
| Search    | `GET /students?search=dela`                                |
| Filter    | `GET /students?program_id=1&year_level=3&status=ACTIVE`    |
| Sort      | `GET /students?sort=last_name` or `sort=-last_name`        |
| Paginate  | `GET /students?page=2&per_page=20` (max 100)               |

Paginated response envelope:

```json
{
  "count": 100,
  "next": "http://.../api/v1/students?page=2&per_page=20",
  "previous": null,
  "page": 1,
  "per_page": 20,
  "last_page": 5,
  "results": [ ... ]
}
```

Invalid pagination values (`page=x`) return 422.

## Error Examples

Validation error (422):

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "student_number": ["student with this student number already exists."]
  }
}
```

Unauthenticated (401):

```json
{
  "success": false,
  "message": "Authentication credentials were not provided.",
  "errors": {}
}
```

Forbidden (403):

```json
{
  "success": false,
  "message": "You do not have permission to perform this action.",
  "errors": {}
}
```

Not found (404):

```json
{
  "success": false,
  "message": "Not found.",
  "errors": {}
}
```