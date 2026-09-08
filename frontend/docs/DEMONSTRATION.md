# Frontend live demonstration

Run `setup.ps1`, then `run.ps1` from the repository root. The login screen displays the
configured base URL. Use `admin@demo.edu` and the private `DEMO_PASSWORD` in
`backend/.env`; never place that password in screenshots or committed configuration.

| PDF task | PyQt6 demonstration |
|---:|---|
| 1 | Swagger `/api/docs` responds; `run.ps1` has started Django |
| 2 | Launch screen displays `http://127.0.0.1:8000/api/v1` |
| 3 | Submit an incorrect password; show the inline 401 message |
| 4 | Log in; sidebar and status bar show name and ADMIN role |
| 5 | Open Students from the authenticated sidebar |
| 6 | Student table displays live records and total count |
| 7 | Enter a surname and press Enter; inspect the filtered API results |
| 8 | Select program/year/status, sorting, Next/Previous; inspect page metadata |
| 9 | Add Student, select a live program, save, and search for the returned record |
| 10 | Repeat the student number; show mapped backend 422 under its field |
| 11 | Select the row, Edit, change a value, and save; list refreshes |
| 12 | Select Deactivate, cancel once, confirm, and observe INACTIVE after refresh |
| 13 | Open Programs or Courses and create/edit an authorized record |
| 14 | Open Academic Terms and Course Offerings; use live relationship selectors |
| 15 | Open Enrollments, select student/offering, save; duplicate shows error |
| 16 | Log in as the assigned instructor; open Grades and update allowed enrollment |
| 17 | As admin select a student and Academic record, or log in as a graded student |
| 18 | As student show missing management routes; backend denial is covered by E2E test |
| 19 | Stop Django, press Refresh, and show the controlled network banner with Retry |
| 20 | Resize below 900/760 px, then explain `ARCHITECTURE.md` and `AI_DEVELOPMENT_LOG.md` |

For a clean 403 demonstration independent of UI hiding, use the backend Postman
collection or run the frontend E2E test; it authenticates as a student and verifies
that `POST /programs` returns 403. This proves the server boundary still applies.
