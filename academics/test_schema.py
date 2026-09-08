from copy import deepcopy
import json

from drf_spectacular.generators import SchemaGenerator
from jsonschema import Draft202012Validator, FormatChecker

from .tests import APITestBase


def json_schema(schema):
    """Translate OpenAPI 3.0 nullable to JSON Schema for response validation."""
    if isinstance(schema, list):
        return [json_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    converted = {key: json_schema(value) for key, value in schema.items() if key != 'nullable'}
    if schema.get('nullable'):
        return {'anyOf': [converted, {'type': 'null'}]}
    return converted


class SchemaContractTests(APITestBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)

    def assert_contract(self, path, data, code='200', method='get'):
        response = self.schema['paths'][path][method]['responses'][code]
        schema = deepcopy(response['content']['application/json']['schema'])
        schema['components'] = self.schema['components']
        Draft202012Validator(json_schema(schema), format_checker=FormatChecker()).validate(data)

    def test_all_resource_and_nested_get_responses_match_openapi(self):
        self.auth(self.token_admin)
        cases = [(f'/api/v1/{name}', f'/api/v1/{name}') for name in
                 ['users', 'programs', 'students', 'courses', 'academic-terms', 'course-offerings', 'enrollments', 'grades']]
        cases += [
            ('/api/v1/auth/me', '/api/v1/auth/me'),
            (f'/api/v1/students/{self.student.pk}', '/api/v1/students/{id}'),
            (f'/api/v1/students/{self.student.pk}/enrollments', '/api/v1/students/{id}/enrollments'),
            (f'/api/v1/students/{self.student.pk}/grades', '/api/v1/students/{id}/grades'),
            (f'/api/v1/students/{self.student.pk}/academic-record', '/api/v1/students/{id}/academic-record'),
            (f'/api/v1/course-offerings/{self.offering.pk}/students', '/api/v1/course-offerings/{id}/students'),
        ]
        for url, path in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assert_contract(path, response.json())

    def test_login_response_matches_openapi(self):
        from .tests import PASSWORD
        response = self.client.post('/api/v1/auth/login', {'email': self.admin.email, 'password': PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assert_contract('/api/v1/auth/login', response.json(), method='post')

    def test_documented_examples_match_their_schemas(self):
        for path, methods in self.schema['paths'].items():
            for method, operation in methods.items():
                if not isinstance(operation, dict):
                    continue
                bodies = list(operation.get('requestBody', {}).get('content', {}).values())
                for response in operation.get('responses', {}).values():
                    bodies.extend(response.get('content', {}).values())
                for body in bodies:
                    if 'example' not in body:
                        continue
                    with self.subTest(path=path, method=method):
                        schema = deepcopy(body['schema'])
                        schema['components'] = self.schema['components']
                        Draft202012Validator(json_schema(schema), format_checker=FormatChecker()).validate(body['example'])

    def test_documentation_is_public(self):
        for path in ['/api/docs', '/api/schema?format=json']:
            self.assertEqual(self.client.get(path).status_code, 200)
