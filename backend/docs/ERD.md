# Entity relationship diagram

```mermaid
erDiagram
    USERS o|--o| STUDENTS : "optional login account"
    PROGRAMS ||--o{ STUDENTS : contains
    USERS ||--o{ COURSE_OFFERINGS : teaches
    COURSES ||--o{ COURSE_OFFERINGS : offered_as
    ACADEMIC_TERMS ||--o{ COURSE_OFFERINGS : schedules
    STUDENTS ||--o{ ENROLLMENTS : registers
    COURSE_OFFERINGS ||--o{ ENROLLMENTS : contains
    ENROLLMENTS ||--o| GRADES : receives
    USERS {
        bigint id PK
        string email UK
        string name
        string password "Django password hash"
        string role "ADMIN REGISTRAR INSTRUCTOR STUDENT"
        boolean is_active
    }
    PROGRAMS {
        bigint id PK
        string code UK
        string name
        text description
        string status
    }
    STUDENTS {
        bigint id PK
        bigint user_id FK,UK "nullable"
        bigint program_id FK
        string student_number UK
        string first_name
        string middle_name
        string last_name "indexed"
        string suffix
        date birth_date "nullable"
        string email
        string contact_number
        text address
        int year_level "1 through 6"
        string status "indexed"
    }
    COURSES {
        bigint id PK
        string course_code UK
        string course_title
        text description
        decimal units "0.5 through 12"
        string status
    }
    ACADEMIC_TERMS {
        bigint id PK
        string academic_year "unique with semester"
        string semester
        date start_date
        date end_date
        string status
    }
    COURSE_OFFERINGS {
        bigint id PK
        bigint course_id FK
        bigint academic_term_id FK
        bigint instructor_id FK
        string section "unique with course and term"
        string schedule
        string room
        int capacity "1 through 1000"
        string status
    }
    ENROLLMENTS {
        bigint id PK
        bigint student_id FK "unique with offering"
        bigint course_offering_id FK
        date enrollment_date
        string status "ENROLLED DROPPED COMPLETED"
    }
    GRADES {
        bigint id PK
        bigint enrollment_id FK,UK
        decimal midterm_grade "nullable 0 through 100"
        decimal final_grade "nullable 0 through 100"
        string remarks
        string status "DRAFT FINALIZED"
    }
```

All eight domain entities have `created_at` and `updated_at`; the diagram omits repeated
timestamps for readability. Django adds its own authentication tables and
`authtoken_token` (one token per user). Actual domain table names have the `academics_`
prefix. The authoritative schema is `academics/migrations/0001_initial.py`.

Domain foreign keys use `PROTECT`: deletion of referenced records returns 409. Unique
constraints prevent duplicate student numbers, course/program codes, user emails,
term/semester combinations, offering sections, enrollments and grades. Check constraints
enforce grade/unit/capacity/year ranges, ordered dates and finalized-grade completeness.
Foreign keys are indexed by Django; student last name and status have explicit indexes.

The user-to-student relationship is optional on both sides. Only an administrator can
link a STUDENT account to a profile. An offering's instructor must be an active
INSTRUCTOR account; that cross-table rule is checked by the API.
