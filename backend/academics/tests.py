from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from .models import (AcademicTerm, Course, CourseOffering, Enrollment, Grade, Program,
                     Student, User)

PASSWORD = 'TestPassword2026!'


def _mk_user(email, role, password=PASSWORD):
    return User.objects.create_user(email=email, password=password, name=email.split('@')[0], role=role)


def _base_attrs(**overrides):
    attrs = {
        'code': 'BSITC', 'name': 'BS Information Tech Test', 'description': 'Test program',
        'status': 'ACTIVE',
    }
    attrs.update(overrides)
    return attrs


class APITestBase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = _mk_user('admin.test@demo.edu', 'ADMIN')
        cls.registrar = _mk_user('registrar.test@demo.edu', 'REGISTRAR')
        cls.instructor = _mk_user('instructor.test@demo.edu', 'INSTRUCTOR')
        cls.instructor2 = _mk_user('instructor2.test@demo.edu', 'INSTRUCTOR')
        cls.program = Program.objects.create(code='BSIT-X', name='Bachelor of Science in IT',
                                             description='Test', status='ACTIVE')
        cls.program2 = Program.objects.create(code='BSCS-X', name='Bachelor of Science in CS',
                                              description='Test', status='ACTIVE')
        cls.course = Course.objects.create(course_code='IT200', course_title='Advanced DB',
                                           units=3, status='ACTIVE')
        cls.course2 = Course.objects.create(course_code='IT201', course_title='Web Dev',
                                            units=3, status='ACTIVE')
        cls.term = AcademicTerm.objects.create(academic_year='2025-2026', semester='FIRST',
                                               start_date=date(2025, 8, 11), end_date=date(2025, 12, 19),
                                               status='ACTIVE')
        cls.offering = CourseOffering.objects.create(course=cls.course, academic_term=cls.term,
                                                     instructor=cls.instructor, section='S1',
                                                     schedule='MW 09:00', capacity=40, status='ACTIVE')
        cls.offering2 = CourseOffering.objects.create(course=cls.course2, academic_term=cls.term,
                                                      instructor=cls.instructor2, section='S2',
                                                      schedule='TTh 10:00', capacity=40, status='ACTIVE')
        cls.student_user = _mk_user('student.test@demo.edu', 'STUDENT')
        cls.student = Student.objects.create(user=cls.student_user, student_number='2026-00001',
                                             first_name='Juan', last_name='Dela Cruz', program=cls.program,
                                             year_level=1, status='ACTIVE')
        cls.student_user2 = _mk_user('student2.test@demo.edu', 'STUDENT')
        cls.student2 = Student.objects.create(user=cls.student_user2, student_number='2026-00002',
                                              first_name='Maria', last_name='Santos', program=cls.program2,
                                              year_level=3, status='ACTIVE')
        cls.enrollment = Enrollment.objects.create(student=cls.student, course_offering=cls.offering,
                                                   status='ENROLLED')
        cls.grade = Grade.objects.create(enrollment=cls.enrollment, midterm_grade=85.0, final_grade=88.0,
                                         remarks='Passed', status='FINALIZED')
        cls.token_admin = Token.objects.create(user=cls.admin)
        cls.token_registrar = Token.objects.create(user=cls.registrar)
        cls.token_instructor = Token.objects.create(user=cls.instructor)
        cls.token_instructor2 = Token.objects.create(user=cls.instructor2)
        cls.token_student = Token.objects.create(user=cls.student_user)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def clear_auth(self):
        self.client.credentials()


class AuthenticationTests(APITestBase):
    def test_valid_login(self):
        resp = self.client.post('/api/v1/auth/login', {'email': 'admin.test@demo.edu', 'password': PASSWORD})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['success'])
        self.assertIn('token', resp.data['data'])
        self.assertEqual(resp.data['data']['user']['email'], 'admin.test@demo.edu')

    def test_invalid_password(self):
        resp = self.client.post('/api/v1/auth/login', {'email': 'admin.test@demo.edu', 'password': 'wrong-password'})
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.data['success'])

    def test_unknown_email(self):
        resp = self.client.post('/api/v1/auth/login', {'email': 'nobody@demo.edu', 'password': PASSWORD})
        self.assertEqual(resp.status_code, 401)

    def test_protected_endpoint_rejects_unauthenticated(self):
        self.clear_auth()
        resp = self.client.get('/api/v1/students')
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.data['success'])

    def test_invalid_token(self):
        self.auth(Token(key='f' * 40))
        resp = self.client.get('/api/v1/auth/me')
        self.assertEqual(resp.status_code, 401)

    def test_me(self):
        self.auth(self.token_admin)
        resp = self.client.get('/api/v1/auth/me')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['data']['email'], 'admin.test@demo.edu')

    def test_logout_invalidates_token(self):
        self.auth(self.token_student)
        resp = self.client.post('/api/v1/auth/logout')
        self.assertEqual(resp.status_code, 204)
        self.clear_auth()
        resp = self.client.get('/api/v1/auth/me', HTTP_AUTHORIZATION=f'Token {self.token_student.key}')
        self.assertEqual(resp.status_code, 401)


class StudentTests(APITestBase):
    def _student_payload(self, **overrides):
        payload = {
            'student_number': '2026-00100',
            'first_name': 'Ana',
            'last_name': 'Reyes',
            'program_id': self.program.id,
            'year_level': 2,
            'status': 'ACTIVE',
            'email': 'ana.reyes@demo.edu',
        }
        payload.update(overrides)
        return payload

    def test_create_student(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/students', self._student_payload())
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['student_number'], '2026-00100')

    def test_duplicate_student_number(self):
        self.auth(self.token_registrar)
        self.client.post('/api/v1/students', self._student_payload())
        resp = self.client.post('/api/v1/students', self._student_payload())
        self.assertEqual(resp.status_code, 422)
        self.assertFalse(resp.data['success'])

    def test_invalid_email(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/students', self._student_payload(email='not-an-email'))
        self.assertEqual(resp.status_code, 422)

    def test_invalid_program(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/students', self._student_payload(program_id=99999))
        self.assertEqual(resp.status_code, 422)

    def test_retrieve(self):
        self.auth(self.token_registrar)
        resp = self.client.get(f'/api/v1/students/{self.student.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['student_number'], '2026-00001')

    def test_not_found(self):
        self.auth(self.token_registrar)
        resp = self.client.get('/api/v1/students/99999')
        self.assertEqual(resp.status_code, 404)

    def test_update(self):
        self.auth(self.token_registrar)
        resp = self.client.patch(f'/api/v1/students/{self.student.id}', {'last_name': 'Ramos'})
        self.assertEqual(resp.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.last_name, 'Ramos')

    def test_student_cannot_access_another_student(self):
        self.auth(self.token_student)
        resp = self.client.get(f'/api/v1/students/{self.student2.id}')
        self.assertEqual(resp.status_code, 404)


class AuthorizationTests(APITestBase):
    def test_admin_can_create_program(self):
        self.auth(self.token_admin)
        resp = self.client.post('/api/v1/programs', _base_attrs(code='BSIS-X'))
        self.assertEqual(resp.status_code, 201)

    def test_student_forbidden_to_create(self):
        self.auth(self.token_student)
        resp = self.client.post('/api/v1/programs', _base_attrs(code='BSIS-Z'))
        self.assertEqual(resp.status_code, 403)

    def test_instructor_forbidden_to_create_student(self):
        self.auth(self.token_instructor)
        resp = self.client.post('/api/v1/students', {
            'student_number': '2026-00999', 'first_name': 'X', 'last_name': 'Y',
            'program_id': self.program.id, 'year_level': 1, 'status': 'ACTIVE',
        })
        self.assertEqual(resp.status_code, 403)

    def test_student_forbidden_to_manage_users(self):
        self.auth(self.token_student)
        resp = self.client.get('/api/v1/users')
        self.assertEqual(resp.status_code, 403)

    def test_registrar_can_manage_students(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/students', {
            'student_number': '2026-00077', 'first_name': 'Leo', 'last_name': 'Lopez',
            'program_id': self.program.id, 'year_level': 1, 'status': 'ACTIVE',
        })
        self.assertEqual(resp.status_code, 201)

    def test_instructor_sees_only_own_offerings(self):
        self.auth(self.token_instructor)
        resp = self.client.get('/api/v1/course-offerings')
        for item in resp.data['results']:
            self.assertEqual(item['instructor_id'], self.instructor.id)


class EnrollmentTests(APITestBase):
    def _payload(self, **overrides):
        payload = {
            'student_id': self.student2.id,
            'course_offering_id': self.offering2.id,
            'status': 'ENROLLED',
        }
        payload.update(overrides)
        return payload

    def test_valid_enrollment(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/enrollments', self._payload())
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_invalid_references(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/enrollments', self._payload(course_offering_id=99999))
        self.assertEqual(resp.status_code, 422)

    def test_duplicate_enrollment_prevented(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/enrollments', {
            'student_id': self.student.id, 'course_offering_id': self.offering.id, 'status': 'ENROLLED',
        })
        self.assertEqual(resp.status_code, 422)

    def test_student_can_see_only_own_enrollments(self):
        self.auth(self.token_student)
        resp = self.client.get('/api/v1/enrollments')
        for item in resp.data['results']:
            self.assertEqual(item['student_id'], self.student.id)

    def test_student_enrollments_action(self):
        self.auth(self.token_student)
        resp = self.client.get(f'/api/v1/students/{self.student.id}/enrollments')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 1)


class GradeTests(APITestBase):
    def test_instructor_can_grade_assigned_offering(self):
        self.auth(self.token_instructor)
        enrollment = Enrollment.objects.create(student=self.student2, course_offering=self.offering,
                                               status='ENROLLED')
        resp = self.client.post('/api/v1/grades', {
            'enrollment_id': enrollment.id, 'midterm_grade': 80, 'final_grade': 85, 'status': 'FINALIZED',
        })
        self.assertEqual(resp.status_code, 201, resp.content)

    def test_instructor_cannot_grade_another_instructors_offering(self):
        self.auth(self.token_instructor2)
        resp = self.client.post('/api/v1/grades', {
            'enrollment_id': self.enrollment.id, 'midterm_grade': 80, 'final_grade': 85,
        })
        self.assertEqual(resp.status_code, 403)

    def test_invalid_finalized_grade_without_rating(self):
        self.auth(self.token_instructor)
        enrollment = Enrollment.objects.create(student=self.student2, course_offering=self.offering,
                                               status='ENROLLED')
        resp = self.client.post('/api/v1/grades', {
            'enrollment_id': enrollment.id, 'status': 'FINALIZED',
        })
        self.assertEqual(resp.status_code, 422)

    def test_grade_score_out_of_range(self):
        self.auth(self.token_instructor)
        enrollment = Enrollment.objects.create(student=self.student2, course_offering=self.offering,
                                               status='ENROLLED')
        resp = self.client.post('/api/v1/grades', {
            'enrollment_id': enrollment.id, 'midterm_grade': 120, 'final_grade': 80,
        })
        self.assertEqual(resp.status_code, 422)

    def test_student_cannot_modify_grades(self):
        self.auth(self.token_student)
        resp = self.client.post('/api/v1/grades', {
            'enrollment_id': self.enrollment.id, 'midterm_grade': 100,
        })
        self.assertEqual(resp.status_code, 403)


class CollectionTests(APITestBase):
    def _make_student(self, number, last_name, program, year, status_='ACTIVE'):
        return Student.objects.create(
            student_number=number, first_name='N', last_name=last_name, program=program,
            year_level=year, status=status_,
        )

    def test_search(self):
        self._make_student('2026-00050', 'Delacruz', self.program, 1)
        self.auth(self.token_registrar)
        resp = self.client.get('/api/v1/students', {'search': 'Delacruz'})
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(len(resp.data['results']), 0)
        self.assertTrue(all('Delacruz' in r['last_name'] for r in resp.data['results']))

    def test_filter(self):
        self._make_student('2026-00051', 'Aguilar', self.program, 4)
        self.auth(self.token_registrar)
        resp = self.client.get('/api/v1/students', {'program_id': self.program.id, 'year_level': 4})
        for r in resp.data['results']:
            self.assertEqual(r['program_id'], self.program.id)
            self.assertEqual(r['year_level'], 4)

    def test_sort(self):
        self.auth(self.token_registrar)
        resp = self.client.get('/api/v1/students', {'sort': 'last_name'})
        names = [r['last_name'] for r in resp.data['results']]
        self.assertEqual(names, sorted(names))

    def test_pagination_metadata(self):
        self.auth(self.token_registrar)
        resp = self.client.get('/api/v1/students', {'page': 1, 'per_page': 5})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['per_page'], 5)
        self.assertIn('last_page', resp.data)
        self.assertGreater(resp.data['count'], 0)

    def test_invalid_pagination(self):
        self.auth(self.token_registrar)
        resp = self.client.get('/api/v1/students', {'page': 'x'})
        self.assertEqual(resp.status_code, 422)


class AcademicRecordTests(APITestBase):
    def test_academic_record_shape(self):
        self.auth(self.token_student)
        resp = self.client.get(f'/api/v1/students/{self.student.id}/academic-record')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['success'])
        self.assertEqual(resp.data['data']['student_id'], self.student.id)
        self.assertEqual(len(resp.data['data']['terms']), 1)
        term = resp.data['data']['terms'][0]
        self.assertEqual(len(term['records']), 1)
        self.assertEqual(term['records'][0]['grade']['final_grade'], '88.00')

    def test_student_cannot_view_another_record(self):
        self.auth(self.token_student)
        resp = self.client.get(f'/api/v1/students/{self.student2.id}/academic-record')
        self.assertEqual(resp.status_code, 404)


class ValidationTests(APITestBase):
    def test_strict_missing_field_rejected(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/programs', {'code': 'XXX'})
        self.assertEqual(resp.status_code, 422)

    def test_unknown_field_rejected(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/programs', _base_attrs(code='YYY', hack='x'))
        self.assertEqual(resp.status_code, 422)

    def test_password_policy_enforced(self):
        self.auth(self.token_admin)
        resp = self.client.post('/api/v1/users', {
            'name': 'New Admin', 'email': 'newadmin@demo.edu', 'role': 'REGISTRAR',
            'password': 'short', 'is_active': True,
        })
        self.assertEqual(resp.status_code, 422)

    def test_academic_term_year_format(self):
        self.auth(self.token_registrar)
        resp = self.client.post('/api/v1/academic-terms', {
            'academic_year': '2025', 'semester': 'FIRST',
            'start_date': '2025-08-11', 'end_date': '2025-12-19',
        })
        self.assertEqual(resp.status_code, 422)
