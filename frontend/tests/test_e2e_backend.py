import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import requests
import pytest
from src.api.client import ApiClient, ApiError


@pytest.fixture(scope='module')
def live_api():
    frontend = Path(__file__).resolve().parents[1]
    backend = frontend.parent / 'backend'
    with tempfile.TemporaryDirectory(prefix='sis-frontend-e2e-') as directory:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        env = dict(os.environ, DATABASE_NAME=str(Path(directory) / 'e2e.sqlite3'),
                   DJANGO_SECRET_KEY='e2e-only-secret-value-that-is-not-used-outside-tests',
                   DEMO_PASSWORD='FrontendE2EPass123!', DJANGO_DEBUG='false', APP_ENV='development')
        commands = [['manage.py', 'migrate', '--noinput'], ['manage.py', 'seed_demo']]
        for args in commands:
            subprocess.run([sys.executable, *args], cwd=backend, env=env, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process = subprocess.Popen([sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}', '--noreload'],
                                   cwd=backend, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f'http://127.0.0.1:{port}/api/v1'
        try:
            for _ in range(60):
                try:
                    if requests.get(base + '/programs', timeout=.2).status_code == 401: break
                except requests.RequestException: time.sleep(.1)
            else: raise RuntimeError('Temporary backend did not start.')
            yield ApiClient(base, timeout=5)
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired: process.kill(); process.wait()


def test_critical_frontend_client_flow_against_real_backend(live_api):
    api = live_api
    user = api.login('admin@demo.edu', 'FrontendE2EPass123!')
    assert user['role'] == 'ADMIN'
    programs = api.list('programs', search='Information', per_page=10)
    assert programs['count'] >= 1
    program = api.create('programs', {'code': 'E2E', 'name': 'Frontend E2E Program'})
    student = api.create('students', {'student_number': 'E2E-00001', 'first_name': 'Front',
                                     'last_name': 'End', 'program_id': program['id'], 'year_level': 1})
    assert api.get('students', student['id'])['student_number'] == 'E2E-00001'
    with pytest.raises(ApiError) as duplicate:
        api.create('students', {'student_number': 'E2E-00001', 'first_name': 'Duplicate',
                                'last_name': 'Student', 'program_id': program['id'], 'year_level': 1})
    assert duplicate.value.status == 422
    api.update('students', student['id'], {'last_name': 'Updated'})
    assert api.list('students', search='Updated', program_id=program['id'])['count'] == 1
    students = api.list('users', role='STUDENT', per_page=1)['results']
    student_email = students[0]['email']
    api.logout(); api.login(student_email, 'FrontendE2EPass123!')
    with pytest.raises(ApiError) as forbidden: api.create('programs', {'code': 'NO', 'name': 'Denied'})
    assert forbidden.value.status == 403
    api.logout(); assert not api.authenticated
