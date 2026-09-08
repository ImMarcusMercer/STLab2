# Screenshot evidence

These images were captured by `scripts/capture_screenshots.py` from the PyQt6 client
while it was connected over HTTP to the seeded Django backend. The capture script reads
the demo password from a process environment variable and does not print or save it.

## Invalid login

![Invalid credential feedback](screenshots/01-invalid-login.png)

## Administrator dashboard

![Administrator role-aware dashboard](screenshots/02-admin-dashboard.png)

## Backend-driven students list

![Students search filter sort and pagination controls](screenshots/03-students-list.png)

## Course offerings module

![Course offerings management](screenshots/04-course-offerings.png)

## Student academic record at a narrow window size

![Student record narrow layout](screenshots/05-student-record-narrow.png)

## Controlled backend-unavailable state

![Network error and retry state](screenshots/06-network-error.png)

The screenshot dataset is evidence from one local run, not application data. Core
records continue to be loaded live whenever the frontend runs.
