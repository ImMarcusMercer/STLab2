# AI development log

This log records engineering assistance, not private reasoning. Human verification
means the listed automated/manual evidence was executed; the student still needs to
read and understand the code before submission.

| Task | AI tool and prompt summary | Result | Review and evidence |
|---|---|---|---|
| Requirements | OpenAI Codex: scan the frontend laboratory PDF and integrate it with the existing API | Requirements matrix for modules, roles, states, tests, evidence and build | Compared against all 14 PDF pages and mapped in `DEMONSTRATION.md` |
| Repository refactor | Codex: reorganize the existing API into backend/frontend applications | Git-tracked backend moved to `backend/`; separate `frontend/`; root orchestration | Backend's 84 tests rerun after the move; Git rename history retained |
| API boundary | Codex: implement a reusable PyQt HTTP client | Environment URL, token header, 204 handling, normalized errors, network timeout | Unit tests cover auth header, 401 clearing, 403/404/409/500, 422 and network failures |
| UI architecture | Codex: build role-aware PyQt6 application modules | Protected stacked navigation, reusable resource pages/dialogs, dashboard and academic record | Offscreen UI tests verify role menus, guard, list rendering, forms and narrow layout |
| Integration | Codex: connect forms and lists to actual backend capabilities | Backend queries, reference selectors, CRUD/deactivation and post-mutation refresh | Temporary real-backend E2E test passes; screenshots use seeded running API |
| UX/error hardening | Codex: satisfy loading/empty/error/responsive requirements | Progress bars, banners, confirmations, inline field errors, network and not-found states | Six inspected screenshots plus targeted UI/client tests |
| Packaging | Codex: provide a reproducible PyQt distributable | PyInstaller spec and build script | Build command and smoke launch documented in test evidence |
| Documentation | Codex: complete required integration documents | README, map, architecture, AI log, demonstration, screenshots and test evidence | Links checked locally; commands rerun from monorepo root |

Important human defense points: client-side navigation is not authorization; the token
is stored only in memory; backend pagination drives the controls; `ApiClient` prevents
duplicated HTTP boilerplate; `ResourcePage` refreshes after mutations; client validation
is advisory and server validation remains authoritative.
