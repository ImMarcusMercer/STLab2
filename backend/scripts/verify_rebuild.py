"""Verify migrations and repeatable seed data in a disposable SQLite database."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='student-api-rebuild-') as directory:
    env = dict(os.environ, DATABASE_NAME=str(Path(directory) / 'rebuild.sqlite3'))
    for command in [['migrate', '--noinput'], ['seed_demo'], ['seed_demo']]:
        completed = subprocess.run([sys.executable, 'manage.py', *command], cwd=root, env=env,
                                   capture_output=True, text=True)
        if completed.returncode:
            # Migration and seeder output contains only operational messages.
            print(completed.stdout)
            print(completed.stderr)
            raise SystemExit(completed.returncode)
        print('PASS ' + ' '.join(command))
    verify = '''
import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from academics.models import User, Program, Student, Course, AcademicTerm, CourseOffering, Enrollment, Grade
models = [User, Program, Student, Course, AcademicTerm, CourseOffering, Enrollment, Grade]
expected = [65, 3, 100, 20, 2, 20, 200, 100]
counts = [model.objects.count() for model in models]
assert counts == expected, counts
for model in models:
    for record in model.objects.all():
        record.full_clean()
print(json.dumps({model.__name__: count for model, count in zip(models, counts)}))
'''
    subprocess.run([sys.executable, '-c', verify], cwd=root, env=env, check=True)
print('PASS clean database rebuild, unchanged seed counts, and validation of all seeded records')
