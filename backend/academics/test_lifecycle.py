from .tests import APITestBase
from .models import Enrollment


class ResourceLifecycleTests(APITestBase):
    def test_create_retrieve_replace_patch_delete_resources(self):
        self.auth(self.token_admin)
        cases = [
            ('users', {'name': 'Lifecycle', 'email': 'lifecycle@example.com', 'role': 'REGISTRAR', 'password': 'LifecyclePass123!'}, {'name': 'Updated'}),
            ('programs', {'code': 'LIFE', 'name': 'Lifecycle'}, {'description': 'Updated'}),
            ('students', {'student_number': 'LIFE', 'first_name': 'Life', 'last_name': 'Cycle', 'program_id': self.program.pk, 'year_level': 1}, {'year_level': 2}),
            ('courses', {'course_code': 'LIFE', 'course_title': 'Lifecycle', 'units': '3.0'}, {'units': '4.0'}),
            ('academic-terms', {'academic_year': '2050-2051', 'semester': 'FIRST', 'start_date': '2050-08-01', 'end_date': '2050-12-01'}, {'end_date': '2050-12-20'}),
            ('course-offerings', {'course_id': self.course.pk, 'academic_term_id': self.term.pk, 'instructor_id': self.instructor.pk, 'section': 'LIFE', 'schedule': 'MW', 'capacity': 10}, {'room': 'Lab 2'}),
            ('enrollments', {'student_id': self.student2.pk, 'course_offering_id': self.offering2.pk}, {'status': 'DROPPED'}),
        ]
        for resource, payload, updates in cases:
            with self.subTest(resource=resource):
                created = self.client.post('/api/v1/' + resource, payload, format='json')
                self.assertEqual(created.status_code, 201, created.data)
                url = f'/api/v1/{resource}/{created.data["id"]}'
                self.assertEqual(self.client.get(url).status_code, 200)
                patched = self.client.patch(url, updates, format='json')
                self.assertEqual(patched.status_code, 200, patched.data)
                for key, value in updates.items():
                    self.assertEqual(patched.data[key], value)
                if resource != 'enrollments':
                    replaced = self.client.put(url, {**payload, **updates}, format='json')
                    self.assertEqual(replaced.status_code, 200, replaced.data)
                self.assertEqual(self.client.delete(url).status_code, 204)
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_grade_create_replace_patch_retrieve(self):
        self.auth(self.token_instructor)
        enrollment = Enrollment.objects.create(student=self.student2, course_offering=self.offering)
        payload = {'enrollment_id': enrollment.pk, 'midterm_grade': '70.00', 'final_grade': '80.00', 'status': 'FINALIZED'}
        created = self.client.post('/api/v1/grades', payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        url = f'/api/v1/grades/{created.data["id"]}'
        self.assertEqual(self.client.put(url, {**payload, 'final_grade': '90.00'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'remarks': 'Passed'}, format='json').status_code, 200)
        self.assertEqual(self.client.get(url).data['final_grade'], '90.00')
