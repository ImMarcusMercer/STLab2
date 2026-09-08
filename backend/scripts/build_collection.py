"""Rebuild the portable Postman acceptance collection; no credentials are embedded."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
groups = []


def group(name):
    item = {'name': name, 'item': []}
    groups.append(item)
    return item['item']


def request(folder, name, method, path, expected=200, body=None, token='admin_token', save=None, checks=()):
    headers = [{'key': 'Content-Type', 'value': 'application/json'}]
    if token:
        headers.append({'key': 'Authorization', 'value': 'Token {{' + token + '}}'})
    req = {'method': method, 'header': headers, 'url': '{{base}}' + path}
    if body is not None:
        req['body'] = {'mode': 'raw', 'raw': json.dumps(body, indent=2), 'options': {'raw': {'language': 'json'}}}
    tests = [f"pm.test('HTTP {expected}', () => pm.response.to.have.status({expected}));"]
    if save:
        variable, expression = save
        tests.append(f"if (pm.response.code === {expected}) pm.collectionVariables.set('{variable}', {expression});")
    tests.extend(checks)
    folder.append({'name': name, 'request': req, 'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': tests}}]})


auth = group('01 Authentication')
request(auth, 'Admin login', 'POST', '/auth/login', body={'email': 'admin@demo.edu', 'password': '{{demo_password}}'}, token=None,
        save=('admin_token', 'pm.response.json().data.token'))
request(auth, 'Invalid password', 'POST', '/auth/login', 401, {'email': 'admin@demo.edu', 'password': 'incorrect'}, token=None)
request(auth, 'Missing authentication', 'GET', '/students', 401, token=None)
request(auth, 'Current user', 'GET', '/auth/me')

users = group('02 Users and Roles')
request(users, 'Create student login', 'POST', '/users', 201,
        {'name': 'Demo Student', 'email': 'student.{{run_id}}@example.com', 'password': '{{demo_password}}', 'role': 'STUDENT'},
        save=('student_user_id', 'pm.response.json().id'))
request(users, 'Create instructor login', 'POST', '/users', 201,
        {'name': 'Demo Instructor', 'email': 'instructor.{{run_id}}@example.com', 'password': '{{demo_password}}', 'role': 'INSTRUCTOR'},
        save=('instructor_id', 'pm.response.json().id'))
request(users, 'List users', 'GET', '/users?role=INSTRUCTOR&per_page=5')

programs = group('03 Programs')
request(programs, 'Create program', 'POST', '/programs', 201, {'code': 'P{{run_id}}', 'name': 'Laboratory Program'}, save=('program_id', 'pm.response.json().id'))
request(programs, 'Retrieve program', 'GET', '/programs/{{program_id}}')
request(programs, 'Update program', 'PATCH', '/programs/{{program_id}}', body={'description': 'Created through the acceptance collection.'})
request(programs, 'List programs', 'GET', '/programs?status=ACTIVE&sort=code')

students = group('04 Students')
student = {'student_number': 'LAB-{{run_id}}', 'first_name': 'Demo', 'last_name': 'Dela Cruz', 'email': 'student.{{run_id}}@example.com',
           'program_id': '{{program_id}}', 'user_id': '{{student_user_id}}', 'year_level': 4}
request(students, 'Create student', 'POST', '/students', 201, student, save=('student_id', 'pm.response.json().id'))
request(students, 'Duplicate student number', 'POST', '/students', 422, student)
request(students, 'Invalid email', 'PATCH', '/students/{{student_id}}', 422, {'email': 'invalid'})
request(students, 'Retrieve student', 'GET', '/students/{{student_id}}')
request(students, 'Update student', 'PATCH', '/students/{{student_id}}', body={'contact_number': '09123456789'})
request(students, 'Search filter sort and paginate', 'GET', '/students?search=Dela&program_id={{program_id}}&year_level=4&sort=last_name&per_page=1', checks=[
    "pm.test('Program filter returns the created student', () => pm.expect(pm.response.json().count).to.equal(1));"])
request(students, 'Not found', 'GET', '/students/999999999', 404)

courses = group('05 Courses')
request(courses, 'Create course', 'POST', '/courses', 201, {'course_code': 'C{{run_id}}', 'course_title': 'API Laboratory', 'units': '3.0'}, save=('course_id', 'pm.response.json().id'))
request(courses, 'Retrieve course', 'GET', '/courses/{{course_id}}')
request(courses, 'Update course', 'PATCH', '/courses/{{course_id}}', body={'description': 'Backend development'})
request(courses, 'List courses', 'GET', '/courses?search=API&sort=course_code')

terms = group('06 Academic Terms')
request(terms, 'Choose a new academic year', 'GET', '/academic-terms?sort=-academic_year&per_page=1', checks=[
    "const rows = pm.response.json().results; const year = rows.length ? Number(rows[0].academic_year.slice(0,4))+1 : 2026;",
    "pm.collectionVariables.set('academic_year', year + '-' + (year+1));",
    "pm.collectionVariables.set('start_date', year + '-08-01'); pm.collectionVariables.set('end_date', year + '-12-20');"])
request(terms, 'Create term', 'POST', '/academic-terms', 201, {'academic_year': '{{academic_year}}', 'semester': 'FIRST', 'start_date': '{{start_date}}', 'end_date': '{{end_date}}'}, save=('term_id', 'pm.response.json().id'))
request(terms, 'Retrieve term', 'GET', '/academic-terms/{{term_id}}')
request(terms, 'Invalid dates', 'PATCH', '/academic-terms/{{term_id}}', 422, {'end_date': '2000-01-01'})

offerings = group('07 Course Offerings')
request(offerings, 'Create offering', 'POST', '/course-offerings', 201,
        {'course_id': '{{course_id}}', 'academic_term_id': '{{term_id}}', 'instructor_id': '{{instructor_id}}', 'section': 'A', 'schedule': 'MW 09:00-10:30', 'room': 'Lab 1', 'capacity': 30}, save=('offering_id', 'pm.response.json().id'))
request(offerings, 'Retrieve offering', 'GET', '/course-offerings/{{offering_id}}')
request(offerings, 'Update offering', 'PATCH', '/course-offerings/{{offering_id}}', body={'room': 'Lab 2'})
request(offerings, 'Filter offerings', 'GET', '/course-offerings?instructor_id={{instructor_id}}')

enrollments = group('08 Enrollments')
enrollment = {'student_id': '{{student_id}}', 'course_offering_id': '{{offering_id}}'}
request(enrollments, 'Enroll student', 'POST', '/enrollments', 201, enrollment, save=('enrollment_id', 'pm.response.json().id'))
request(enrollments, 'Prevent duplicate enrollment', 'POST', '/enrollments', 422, enrollment)
request(enrollments, 'Invalid offering reference', 'POST', '/enrollments', 422, {**enrollment, 'course_offering_id': 99999999})
request(enrollments, 'Student enrollments', 'GET', '/students/{{student_id}}/enrollments')
request(enrollments, 'Offering roster', 'GET', '/course-offerings/{{offering_id}}/students')

grades = group('09 Grades')
request(grades, 'Instructor login', 'POST', '/auth/login', body={'email': 'instructor.{{run_id}}@example.com', 'password': '{{demo_password}}'}, token=None, save=('instructor_token', 'pm.response.json().data.token'))
request(grades, 'Encode authorized grade', 'POST', '/grades', 201,
        {'enrollment_id': '{{enrollment_id}}', 'midterm_grade': '85.00', 'final_grade': '90.00', 'status': 'FINALIZED'}, token='instructor_token', save=('grade_id', 'pm.response.json().id'))
request(grades, 'Update authorized grade', 'PATCH', '/grades/{{grade_id}}', body={'final_grade': '92.00'}, token='instructor_token')
request(grades, 'Out-of-range grade', 'PATCH', '/grades/{{grade_id}}', 422, {'final_grade': 101}, token='instructor_token')
request(grades, 'Instructor cannot view full transcript', 'GET', '/students/{{student_id}}/academic-record', 403, token='instructor_token')

records = group('10 Academic Records and Student Permissions')
request(records, 'Student login', 'POST', '/auth/login', body={'email': 'student.{{run_id}}@example.com', 'password': '{{demo_password}}'}, token=None, save=('student_token', 'pm.response.json().data.token'))
request(records, 'Own profile', 'GET', '/students/{{student_id}}', token='student_token')
request(records, 'Own grades', 'GET', '/students/{{student_id}}/grades', token='student_token')
request(records, 'Own academic record', 'GET', '/students/{{student_id}}/academic-record', token='student_token', checks=[
    "pm.test('Record has finalized grade', () => pm.expect(pm.response.json().data.terms[0].records[0].grade.final_grade).to.equal('92.00'));"])
request(records, 'Other student is hidden', 'GET', '/students/1/academic-record', 404, token='student_token')
request(records, 'Student cannot modify grades', 'PATCH', '/grades/{{grade_id}}', 403, {'final_grade': 100}, token='student_token')
request(records, 'Student cannot create programs', 'POST', '/programs', 403, {'code': 'DENIED', 'name': 'Denied'}, token='student_token')
request(records, 'Logout student', 'POST', '/auth/logout', 204, token='student_token')
request(records, 'Revoked token rejected', 'GET', '/auth/me', 401, token='student_token')

deletes = group('11 Deletion and Referential Integrity')
request(deletes, 'Protect referenced program', 'DELETE', '/programs/{{program_id}}', 409)
request(deletes, 'Create disposable program', 'POST', '/programs', 201, {'code': 'D{{run_id}}', 'name': 'Disposable'}, save=('delete_id', 'pm.response.json().id'))
request(deletes, 'Delete unreferenced program', 'DELETE', '/programs/{{delete_id}}', 204)
request(deletes, 'Deleted resource is not found', 'GET', '/programs/{{delete_id}}', 404)
request(deletes, 'Logout admin', 'POST', '/auth/logout', 204)

collection = {
    'info': {'name': 'Student Information API - Acceptance Demonstration',
             'description': 'Set demo_password to your local DEMO_PASSWORD, then run all folders in order against a seeded local database. IDs and tokens are captured automatically. Each run adds demonstration records. Never export populated token/password variables.',
             'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'},
    'variable': [{'key': 'base', 'value': 'http://127.0.0.1:8000/api/v1'}, {'key': 'demo_password', 'value': ''}],
    'event': [{'listen': 'prerequest', 'script': {'type': 'text/javascript', 'exec': [
        "if (pm.info.requestName === 'Admin login') pm.collectionVariables.set('run_id', Date.now().toString());"]}}],
    'item': groups,
}
destination = ROOT / 'docs/student-information-api.postman_collection.json'
destination.write_text(json.dumps(collection, indent=2) + '\n', encoding='utf-8')
print(f'Wrote {sum(len(g["item"]) for g in groups)} requests to {destination.name}')
