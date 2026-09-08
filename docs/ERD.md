# Entity Relationship Diagram (ERD)

## Relationships

```
users 1───0..1 students
programs 1───* students
courses 1───* course_offerings
academic_terms 1───* course_offerings
users (instructor) 1───* course_offerings
students 1───* enrollments
course_offerings 1───* enrollments
enrollments 1───0..1 grades (OneToOne)
```

## Text ERD

```
+------------------+       +------------------+
| users            |       | programs         |
|------------------|       |------------------|
| id PK            |       | id PK            |
| name             | 1   1 | code UQ          |
| email UQ         |O------O| name             |
| password_hash    |  0..1 | description      |
| role             |       | status           |
| is_active        |       | created_at       |
| created_at       |       | updated_at       |
| updated_at       |       +------------------+
+------------------+               |
                                   | 1
                                   |
                                   | *
                                   v
        +------------------+       +------------------+
        | students         |       | (program FK)     |
        |------------------|       +------------------+
        | id PK            |
        | student_number UQ|
        | first_name       |
        | middle_name      |
        | last_name (idx)  |
        | suffix           |
        | birth_date       |
        | email            |
        | contact_number   |
        | address          |
        | program_id FK -> programs.id
        | user_id FK  -> users.id (1..0..1)
        | year_level  (1-6)
        | status (idx)
        | created_at / updated_at
        +------------------+
```

```
+------------------+       +------------------+
| academic_terms   |       | courses          |
|------------------|       |------------------|
| id PK            |       | id PK            |
| academic_year    | 1     | course_code UQ   |
| semester         |O------| course_title     |
| start_date       |   *   | description      |
| end_date         |       | units (0.5-12)   |
| status           |       | status           |
| created_at       |       | created_at       |
| updated_at       |       | updated_at       |
+------------------+       +------------------+
        |                           |
        | 1                         | 1
        | *                         | *
        v                           v
+-----------------------------------------------------------------------------------+
| course_offerings                                                                    |
| id PK                                                                              |
| course_id FK -> courses.id                                                         |
| academic_term_id FK -> academic_terms.id                                           |
| instructor_id FK -> users.id                                                       |
| section            (course + term + section UNIQUE)                                |
| schedule / room / capacity (1-1000) / status                                       |
| created_at / updated_at                                                            |
+-----------------------------------------------------------------------------------+
        | 1
        | *
        v
+-----------------------------------------------------------------------------------+
| enrollments                                                                        |
| id PK                                                                              |
| student_id FK -> students.id                                                       |
| course_offering_id FK -> course_offerings.id                                       |
| enrollment_date                                                                    |
| status  (ENROLLED / DROPPED / COMPLETED)                                           |
| created_at / updated_at                                                            |
| UNIQUE (student_id, course_offering_id)   -- duplicate enrollment prevention       |
+-----------------------------------------------------------------------------------+
        | 1
        | 0..1
        v
+-----------------------------------------------------------------------------------+
| grades                                                                             |
| id PK                                                                              |
| enrollment_id FK -> enrollments.id (OneToOne, UNIQUE)                              |
| midterm_grade (0-100, nullable)                                                    |
| final_grade   (0-100, nullable; required when FINALIZED)                           |
| remarks                                                                             |
| status (DRAFT / FINALIZED)                                                          |
| created_at / updated_at                                                             |
+-----------------------------------------------------------------------------------+
```

## Integrity Notes

- `student_number` and `course_code` are unique (`UQ`) at the database level.
- `email` on `users` is unique and used as the login identifier.
- Foreign keys use `on_delete=PROTECT` so referenced records cannot vanish silently;
  conflicting deletes raise a 409 (use status `INACTIVE` to deactivate).
- Check constraints: `year_level` between 1 and 6, `units` between 0.5 and 12,
  `capacity` between 1 and 1000, grade values between 0 and 100, term end >= start.
- `Index` on `students.last_name` and `students.status` support the most frequent search
  and filter paths.
- Duplicate enrollment in the same offering is prevented by a unique constraint plus a
  serializer check.

## Database

SQLite (default `db.sqlite3`), reproducible from `academics/migrations/`. To run on
PostgreSQL/MySQL instead, swap `DATABASES` in `config/settings.py` and apply the same
migrations (they are engine-agnostic).