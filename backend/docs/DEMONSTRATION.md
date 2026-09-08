# Mandatory laboratory demonstration

Start a seeded local server and open `/api/docs`. Import the Postman collection, set
`demo_password`, and run its numbered folders in order. The collection captures IDs
and tokens, so no manual ID substitution is needed. Each run creates additional demo
records. For command-line verification, Node.js 22+ is needed only for this optional
collection runner:

```powershell
.\.venv\Scripts\python scripts/run_demo.py
```

The runner sends the actual collection HTTP requests and executes its Postman assertion
scripts through a small Node adapter. It does not implement all of Postman's scripting
APIs; it supports the APIs used by this checked-in collection. Credentials stay in
memory and are never printed or saved into the collection.

| PDF case | Demonstration |
|---:|---|
| 1 | Run `migrate`, `seed_demo`, then `runserver`; list programs |
| 2 | Authentication / Admin login |
| 3 | Authentication / Missing authentication (401) |
| 4 | Programs / Create program (201) |
| 5 | Students / Create student (201) |
| 6 | Students / Duplicate student number and Invalid email (422) |
| 7 | Students / Retrieve student and Update student |
| 8 | Students / Search filter sort and paginate |
| 9 | Same request uses `sort=last_name&per_page=1`; inspect pagination metadata |
| 10 | Courses / Create course; Academic Terms / Create term |
| 11 | Course Offerings / Create offering |
| 12 | Enrollments / Enroll student |
| 13 | Enrollments / Prevent duplicate enrollment (422) |
| 14 | Grades / Encode authorized grade and Update authorized grade |
| 15 | Academic Records / Own academic record |
| 16 | Student cannot modify grades (403); Instructor cannot view full transcript (403) |
| 17 | Students / Not found (404) |
| 18 | Open `/api/docs` and inspect request/response schemas |
| 19 | Run `python manage.py test academics --verbosity 2` |
| 20 | Explain `AtomicViewSet` and `EnrollmentSerializer.validate`; demonstrate a small rule change and regression test |

Additional requests demonstrate invalid references, out-of-range grades, account
isolation, token revocation, referenced-delete conflicts and successful deletion of
an unreferenced resource. Automated tests additionally exercise registrar permissions,
another instructor's grades, password changes, seeder idempotency and concurrent seats.

Human explanation and live modification (case 20) remain the student's responsibility.
