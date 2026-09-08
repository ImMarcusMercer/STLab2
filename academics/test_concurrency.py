from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .models import User, Program, Student, Course, AcademicTerm, CourseOffering, Enrollment


class CapacityConcurrencyTests(TransactionTestCase):
    def test_two_requests_cannot_take_the_last_seat(self):
        admin = User.objects.create_user('admin@concurrency.example', role='ADMIN', name='Admin')
        token = Token.objects.create(user=admin)
        instructor = User.objects.create_user('teacher@concurrency.example', role='INSTRUCTOR', name='Instructor')
        program = Program.objects.create(code='P', name='Program')
        students = [Student.objects.create(student_number=str(i), first_name='Student', last_name=str(i),
                                          program=program, year_level=1) for i in range(2)]
        course = Course.objects.create(course_code='C', course_title='Course', units=3)
        term = AcademicTerm.objects.create(academic_year='2026-2027', semester='FIRST',
                                           start_date=date(2026, 8, 1), end_date=date(2026, 12, 20))
        offering = CourseOffering.objects.create(course=course, academic_term=term, instructor=instructor,
                                                 section='A', schedule='MW', capacity=1)
        barrier = Barrier(2)

        def enroll(student_id):
            close_old_connections()
            try:
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
                barrier.wait(timeout=10)
                return client.post('/api/v1/enrollments', {'student_id': student_id,
                                                          'course_offering_id': offering.pk}).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            codes = list(pool.map(enroll, [student.pk for student in students]))
        self.assertEqual(codes.count(201), 1, codes)
        self.assertTrue(all(code in (201, 422, 503) for code in codes), codes)
        self.assertEqual(Enrollment.objects.filter(course_offering=offering).count(), 1)
        # SQLite may return a retryable lock error; retry must still respect capacity.
        loser = next(student for student in students if not Enrollment.objects.filter(student=student).exists())
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.assertEqual(client.post('/api/v1/enrollments', {'student_id': loser.pk,
                                                            'course_offering_id': offering.pk}).status_code, 422)
