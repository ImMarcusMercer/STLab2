"""Capture reproducible UI evidence against a running backend.

Set SIS_DEMO_PASSWORD in the process environment. This script never saves or prints it.
"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from PyQt6.QtWidgets import QApplication
from src.api.client import ApiClient
from src.config import Settings
from src.ui.main_window import MainWindow
from src.ui.theme import APP_STYLE


def wait(app, condition, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition(): return
        time.sleep(.03)
    raise RuntimeError('Timed out waiting for UI state.')


def shot(window, path):
    QApplication.processEvents()
    if not window.grab().save(str(path)):
        raise RuntimeError(f'Could not save {path.name}')
    print('Captured ' + path.name)


def main():
    password = os.getenv('SIS_DEMO_PASSWORD')
    if not password: raise SystemExit('Set SIS_DEMO_PASSWORD to the local seeded account password.')
    app = QApplication([]); app.setStyle('Fusion'); app.setStyleSheet(APP_STYLE)
    settings = Settings.load(); output = root / 'docs/screenshots'; output.mkdir(parents=True, exist_ok=True)
    api = ApiClient(settings.api_base_url); window = MainWindow(api, settings); window.show()
    window.login.email.setText('admin@demo.edu'); window.login.password.setText('incorrect'); window.login.login()
    wait(app, lambda: window.login.error.isVisible() and not window.login.busy.isVisible())
    shot(window, output / '01-invalid-login.png')
    api.login('admin@demo.edu', password); window._authenticated(api.user)
    wait(app, lambda: all(label.text() != '—' for label in window.pages['dashboard'].cards.values()))
    shot(window, output / '02-admin-dashboard.png')
    window.navigate('students'); page = window.pages['students']
    wait(app, lambda: page.table.rowCount() > 0 and not page.busy.isVisible())
    shot(window, output / '03-students-list.png')
    window.navigate('course-offerings'); page = window.pages['course-offerings']
    wait(app, lambda: page.table.rowCount() > 0 and not page.busy.isVisible())
    shot(window, output / '04-course-offerings.png')
    student_email = None
    for grade in api.list('grades', per_page=100)['results']:
        enrollment = api.get('enrollments', grade['enrollment_id'])
        student = api.get('students', enrollment['student_id'])
        if student.get('user_id'):
            student_email = api.get('users', student['user_id'])['email']; break
    if not student_email: raise RuntimeError('No graded student with a linked login account was found.')
    api.logout(); api.login(student_email, password); window._authenticated(api.user); window.resize(800, 600)
    window.navigate('records'); record = window.pages['records']
    wait(app, lambda: record.cards.count() > 1 and not record.busy.isVisible())
    shot(window, output / '05-student-record-narrow.png')
    unreachable = ApiClient('http://127.0.0.1:1/api/v1', timeout=1)
    unreachable.token = 'demonstration'; unreachable.user = {'id': 1, 'name': 'Offline Demo', 'email': 'offline@example.com', 'role': 'ADMIN', 'is_active': True}
    offline = MainWindow(unreachable, Settings(unreachable.base_url, 1)); offline.show(); offline._authenticated(unreachable.user); offline.navigate('students')
    wait(app, lambda: offline.pages['students'].banner.isVisible(), timeout=5)
    shot(offline, output / '06-network-error.png')
    offline.close(); window.close()


if __name__ == '__main__': main()
