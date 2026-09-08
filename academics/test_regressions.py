from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token

from .models import AcademicTerm, Course, CourseOffering, Enrollment, Grade, Program, Student, User
from .tests import APITestBase, PASSWORD


class SecurityRegressionTests(APITestBase):
    def test_expired_token_rejected(self):
        Token.objects.filter(pk=self.token_admin.pk).update(created=timezone.now() - timedelta(days=2))
        self.auth(self.token_admin)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)

    def test_login_renews_expired_token_even_with_stale_header(self):
        Token.objects.filter(pk=self.token_admin.pk).update(created=timezone.now() - timedelta(days=2))
        self.auth(self.token_admin)
        response = self.client.post('/api/v1/auth/login', {'email': self.admin.email, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotEqual(response.data['data']['token'], self.token_admin.key)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + response.data['data']['token'])
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 200)

    def test_deactivated_account_rejected_for_login_and_token(self):
        self.admin.is_active = False
        self.admin.save()
        self.auth(self.token_admin)
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)
        response = self.client.post('/api/v1/auth/login', {'email': self.admin.email, 'password': PASSWORD})
        self.assertEqual(response.status_code, 401)

    def test_student_cannot_access_other_students_nested_resources(self):
        self.auth(self.token_student)
        for suffix in ['', '/enrollments', '/grades', '/academic-record']:
            with self.subTest(suffix=suffix):
                self.assertEqual(self.client.get(f'/api/v1/students/{self.student2.pk}{suffix}').status_code, 404)

    def test_instructor_cannot_read_full_academic_history_or_profile(self):
        self.auth(self.token_instructor)
        for suffix in ['', '/enrollments', '/grades', '/academic-record']:
            with self.subTest(suffix=suffix):
                self.assertEqual(self.client.get(f'/api/v1/students/{self.student.pk}{suffix}').status_code, 403)

    def test_instructor_cannot_update_other_grade(self):
        self.auth(self.token_instructor2)
        self.assertEqual(self.client.patch(f'/api/v1/grades/{self.grade.pk}', {'final_grade': 100}).status_code, 404)
        self.grade.refresh_from_db()
        self.assertEqual(self.grade.final_grade, 88)

    def test_student_cannot_read_other_enrollment_or_grade(self):
        enrollment = Enrollment.objects.create(student=self.student2, course_offering=self.offering2)
        grade = Grade.objects.create(enrollment=enrollment, final_grade=90)
        self.auth(self.token_student)
        self.assertEqual(self.client.get(f'/api/v1/enrollments/{enrollment.pk}').status_code, 404)
        self.assertEqual(self.client.get(f'/api/v1/grades/{grade.pk}').status_code, 404)

    def test_roster_is_scoped_and_omits_private_contact_data(self):
        self.auth(self.token_instructor)
        response = self.client.get(f'/api/v1/course-offerings/{self.offering.pk}/students')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertNotIn('address', response.data['results'][0])
        self.assertNotIn('birth_date', response.data['results'][0])
        self.assertEqual(self.client.get(f'/api/v1/course-offerings/{self.offering2.pk}/students').status_code, 404)
        self.auth(self.token_student)
        self.assertEqual(self.client.get(f'/api/v1/course-offerings/{self.offering.pk}/students').status_code, 403)

    def test_registrar_cannot_reassign_account_ownership(self):
        self.auth(self.token_registrar)
        response = self.client.patch(f'/api/v1/students/{self.student.pk}', {'user_id': None}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_delete_self(self):
        self.auth(self.token_admin)
        self.assertEqual(self.client.delete(f'/api/v1/users/{self.admin.pk}').status_code, 403)

    def test_password_update_invalidates_old_token_and_hash_is_hidden(self):
        self.auth(self.token_admin)
        response = self.client.patch(f'/api/v1/users/{self.admin.pk}', {'password': 'DifferentPass123!'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('password', response.data)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('DifferentPass123!'))
        self.assertEqual(self.client.get('/api/v1/auth/me').status_code, 401)

    def test_cannot_escalate_via_undeclared_user_fields(self):
        self.auth(self.token_admin)
        response = self.client.patch(f'/api/v1/users/{self.registrar.pk}', {'is_superuser': True}, format='json')
        self.assertEqual(response.status_code, 422)

    def test_login_rate_limited(self):
        cache.clear()
        for _ in range(10):
            self.client.post('/api/v1/auth/login', {'email': 'nobody@example.com', 'password': 'incorrect'})
        response = self.client.post('/api/v1/auth/login', {'email': 'nobody@example.com', 'password': 'incorrect'})
        self.assertEqual(response.status_code, 429)
        cache.clear()


class IntegrityRegressionTests(APITestBase):
    def setUp(self):
        self.auth(self.token_admin)

    def test_full_offering_cannot_accept_another_student(self):
        self.offering.capacity = 1
        self.offering.save()
        response = self.client.post('/api/v1/enrollments', {'student_id': self.student2.pk, 'course_offering_id': self.offering.pk})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.offering.enrollments.count(), 1)

    def test_capacity_cannot_be_reduced_below_occupied_seats(self):
        Enrollment.objects.create(student=self.student2, course_offering=self.offering)
        self.assertEqual(self.client.patch(f'/api/v1/course-offerings/{self.offering.pk}', {'capacity': 1}).status_code, 422)

    def test_inactive_student_cannot_enroll(self):
        self.student2.status = 'INACTIVE'
        self.student2.save()
        self.assertEqual(self.client.post('/api/v1/enrollments', {'student_id': self.student2.pk, 'course_offering_id': self.offering2.pk}).status_code, 422)

    def test_enrollment_links_immutable(self):
        self.assertEqual(self.client.patch(f'/api/v1/enrollments/{self.enrollment.pk}', {'student_id': self.student2.pk}).status_code, 422)

    def test_graded_enrollment_cannot_be_dropped_or_deleted(self):
        self.assertEqual(self.client.patch(f'/api/v1/enrollments/{self.enrollment.pk}', {'status': 'DROPPED'}).status_code, 422)
        self.assertEqual(self.client.delete(f'/api/v1/enrollments/{self.enrollment.pk}').status_code, 409)

    def test_invalid_grade_enrollment(self):
        self.assertEqual(self.client.post('/api/v1/grades', {'enrollment_id': 999999, 'final_grade': 80}).status_code, 422)

    def test_dropped_enrollment_cannot_be_graded(self):
        enrollment = Enrollment.objects.create(student=self.student2, course_offering=self.offering2, status='DROPPED')
        self.assertEqual(self.client.post('/api/v1/grades', {'enrollment_id': enrollment.pk, 'final_grade': 80}).status_code, 422)

    def test_invalid_instructor_role(self):
        response = self.client.patch(f'/api/v1/course-offerings/{self.offering.pk}', {'instructor_id': self.student_user.pk})
        self.assertEqual(response.status_code, 422)

    def test_invalid_status_and_year(self):
        for payload in [{'status': 'HACKED'}, {'year_level': 0}, {'year_level': 7}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch(f'/api/v1/students/{self.student.pk}', payload).status_code, 422)

    def test_invalid_date_order_on_partial_update(self):
        self.assertEqual(self.client.patch(f'/api/v1/academic-terms/{self.term.pk}', {'end_date': '2020-01-01'}).status_code, 422)

    def test_referenced_program_delete_conflicts(self):
        response = self.client.delete(f'/api/v1/programs/{self.program.pk}')
        self.assertEqual(response.status_code, 409)
        self.assertNotIn('academics_', str(response.data))

    def test_database_duplicate_enrollment_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Enrollment.objects.create(student=self.student, course_offering=self.offering)

    def test_database_grade_range_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Grade.objects.filter(pk=self.grade.pk).update(final_grade=101)


class CollectionRegressionTests(APITestBase):
    def setUp(self):
        self.auth(self.token_admin)

    def test_program_id_filter_excludes_other_programs(self):
        # Both students share a year; an ignored program filter must fail this test.
        Student.objects.filter(pk=self.student2.pk).update(year_level=self.student.year_level)
        response = self.client.get('/api/v1/students', {'program_id': self.program.pk})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.student.pk)

    def test_foreign_key_filters(self):
        Enrollment.objects.create(student=self.student2, course_offering=self.offering2)
        for path, query, count in [
            ('course-offerings', {'instructor_id': self.instructor2.pk}, 1),
            ('course-offerings', {'course_id': self.course2.pk}, 1),
            ('enrollments', {'student_id': self.student2.pk}, 1),
            ('enrollments', {'course_offering_id': self.offering2.pk}, 1),
            ('grades', {'enrollment_id': 999999}, 0),
        ]:
            with self.subTest(path=path, query=query):
                self.assertEqual(self.client.get(f'/api/v1/{path}', query).data['count'], count)

    def test_nested_collections_are_paginated(self):
        second = Enrollment.objects.create(student=self.student, course_offering=self.offering2)
        Grade.objects.create(enrollment=second, final_grade=75)
        Enrollment.objects.create(student=self.student2, course_offering=self.offering)
        for path in [f'students/{self.student.pk}/enrollments', f'students/{self.student.pk}/grades',
                     f'course-offerings/{self.offering.pk}/students']:
            with self.subTest(path=path):
                response = self.client.get('/api/v1/' + path, {'per_page': 1})
                self.assertEqual(response.data['count'], 2)
                self.assertEqual(len(response.data['results']), 1)
                self.assertIsNotNone(response.data['next'])

    def test_academic_record_pages_enrollments_before_grouping(self):
        Enrollment.objects.create(student=self.student, course_offering=self.offering2)
        response = self.client.get(f'/api/v1/students/{self.student.pk}/academic-record', {'per_page': 1})
        data = response.data['data']
        self.assertEqual(data['pagination']['count'], 2)
        self.assertEqual(sum(len(term['records']) for term in data['terms']), 1)
        self.assertIsNotNone(data['pagination']['next'])

    def test_page_size_capped_and_invalid_sort_rejected(self):
        self.assertEqual(self.client.get('/api/v1/students', {'per_page': 10000}).data['per_page'], 100)
        self.assertEqual(self.client.get('/api/v1/students', {'sort': 'password'}).status_code, 422)

    def test_malformed_json_and_unknown_route(self):
        response = self.client.post('/api/v1/students', '{invalid', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data['success'])
        response = self.client.get('/api/v1/no-such-route')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['success'])

    def test_unexpected_exception_does_not_leak(self):
        with patch('academics.views.StudentViewSet.get_queryset', side_effect=RuntimeError('private database password')):
            response = self.client.get('/api/v1/students')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('private', str(response.data))


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class SeedRegressionTests(APITestBase):
    def test_seeding_is_repeatable_and_minimum_counts_hold(self):
        call_command('seed_demo', password=PASSWORD, stdout=StringIO())
        models = [User, Program, Student, Course, AcademicTerm, CourseOffering, Enrollment, Grade]
        first = [model.objects.count() for model in models]
        call_command('seed_demo', password=PASSWORD, stdout=StringIO())
        self.assertEqual(first, [model.objects.count() for model in models])
        for actual, minimum in zip(first, [5, 3, 100, 20, 2, 20, 200, 100]):
            self.assertGreaterEqual(actual, minimum)
        for user in User.objects.filter(email__endswith='student.demo.edu'):
            self.assertNotIn(' ', user.email)
