# API integration map

All paths are relative to `FRONTEND_API_BASE_URL`. Main collection pages send `page`,
`per_page`, `search`, documented filters, and `sort` where supported. Write controls
appear only for roles listed below; the backend verifies every request independently.

| Frontend page or feature | Endpoint(s) and method | Visible roles / purpose |
|---|---|---|
| Login | `POST /auth/login` | Public; establish token and user state |
| Current identity | `GET /auth/me` | Authenticated; profile/session verification |
| Logout | `POST /auth/logout` | Authenticated; revoke token, expect 204 |
| Dashboard | `GET /students`, `/programs`, `/courses`, `/course-offerings`, `/enrollments`, `/grades` with `per_page=1` | Counts only resources visible to the role |
| Users & roles | `GET/POST /users`; `GET/PATCH/DELETE /users/{id}` | Administrator only |
| Students list | `GET /students` | Admin/registrar management; backend search/filter/sort/page |
| Student create | `POST /students` | Admin/registrar; admin may link account |
| Student view/edit | `GET/PATCH /students/{id}` | Admin/registrar; student own profile is reached through My Record flow |
| Student deactivate | `PATCH /students/{id}` with `status=INACTIVE` | Admin/registrar; confirmation required |
| Student academic record | `GET /students/{id}/academic-record?per_page=100` | Staff-selected student or student's own linked profile |
| Programs | `GET/POST /programs`; `GET/PATCH/DELETE /programs/{id}` | Catalog read for all; writes admin/registrar |
| Courses | `GET/POST /courses`; `GET/PATCH/DELETE /courses/{id}` | Catalog read for all; writes admin/registrar |
| Academic terms | `GET/POST /academic-terms`; `GET/PATCH/DELETE /academic-terms/{id}` | Catalog read for all; writes admin/registrar |
| Course offerings | `GET/POST /course-offerings`; `GET/PATCH/DELETE /course-offerings/{id}` | Admin/registrar manage; instructor sees assigned only |
| Offering reference selectors | `GET /courses`, `/academic-terms`, `/users?role=INSTRUCTOR` | Load meaningful choices before submission |
| Enrollments | `GET/POST /enrollments`; `GET/PATCH/DELETE /enrollments/{id}` | Admin/registrar manage; instructor sees assigned; student record renders own data |
| Enrollment selectors | `GET /students`, `/course-offerings` | Authorized live relationship choices |
| Grades | `GET/POST /grades`; `GET/PATCH /grades/{id}` | Admin/registrar/instructor writes allowed scope; no delete endpoint |
| Grade selector | `GET /enrollments` | Role-scoped enrollment choices |
| My Academic Record | `GET /students?per_page=1`, then `GET /students/{id}/academic-record` | Student only; first call resolves linked own profile |
| API connection view | No request; displays configured base URL and current in-memory identity | Authenticated profile page |

The generic list/form code keeps endpoint strings in `resources.py`; authentication
paths live only in `api/client.py`. If the backend contract changes, update those two
boundaries and their tests before changing presentation pages.
