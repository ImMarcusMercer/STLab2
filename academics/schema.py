_ERROR_SCHEMA = {
    'type': 'object',
    'properties': {
        'success': {'type': 'boolean', 'enum': [False]},
        'message': {'type': 'string'},
        'errors': {
            'type': 'object',
            'additionalProperties': {},
        },
    },
    'required': ['success', 'message', 'errors'],
}

_ERRORS = {
    400: ('Bad Request', {'success': False, 'message': 'Bad request.', 'errors': {}}),
    401: ('Unauthorized', {'success': False,
                          'message': 'Authentication credentials were not provided.', 'errors': {}}),
    403: ('Forbidden', {'success': False,
                       'message': 'You do not have permission to perform this action.', 'errors': {}}),
    404: ('Not Found', {'success': False, 'message': 'Not found.', 'errors': {}}),
    409: ('Conflict', {'success': False, 'message': 'Resource is referenced by other records.', 'errors': {}}),
    422: ('Validation Failed', {'success': False, 'message': 'Validation failed.',
                                'errors': {'email': ['A valid email address is required.']}}),
    429: ('Too Many Requests', {'success': False, 'message': 'Request was throttled.', 'errors': {}}),
    500: ('Server Error', {'success': False, 'message': 'Internal server error.', 'errors': {}}),
    503: ('Unavailable', {'success': False, 'message': 'Database temporarily unavailable. Retry the request.', 'errors': {}}),
}


def _error_response(code):
    _, payload = _ERRORS[code]
    return {
        'description': _ERRORS[code][0],
        'content': {'application/json': {'schema': _ERROR_SCHEMA, 'example': payload}},
    }


def add_errors(result, generator, request, public):
    """Suffix the documented error responses for every operation."""
    for path in result.get('paths', {}).values():
        for operation in path.values():
            if not isinstance(operation, dict) or 'responses' not in operation:
                continue
            responses = operation.setdefault('responses', {})
            for code in _ERRORS:
                responses[str(code)] = _error_response(code)
    return result


def add_examples(result, generator, request, public):
    """Keep Swagger's executable examples aligned with the generated schemas."""
    values = {
        'email': 'student@example.com', 'password': 'YourLocalPassword123!',
        'token': 'example-token-obtain-a-real-one-from-login', 'name': 'Sample Program',
        'first_name': 'Ana', 'last_name': 'Santos', 'middle_name': '', 'suffix': '',
        'student_number': '2026-99999', 'code': 'BSIT', 'course_code': 'LAB101',
        'course_title': 'REST API Laboratory', 'units': '3.0', 'academic_year': '2026-2027',
        'semester': 'FIRST', 'section': 'A', 'schedule': 'MW 09:00-10:30', 'room': 'Lab 1',
        'capacity': 30, 'year_level': 1, 'midterm_grade': '85.00', 'final_grade': '90.00',
        'start_date': '2026-08-01', 'end_date': '2026-12-20', 'birth_date': '2005-01-01',
        'enrollment_date': '2026-08-01', 'count': 1, 'page': 1, 'last_page': 1, 'per_page': 20,
        'next': None, 'previous': None, 'full_name': 'Ana Santos', 'program': 'BSIT',
        'remarks': 'Passed', 'description': 'Laboratory example',
    }

    def sample(schema, key='', depth=0):
        if depth > 25:
            return None
        if '$ref' in schema:
            target = result
            for part in schema['$ref'].split('/')[1:]:
                target = target[part]
            return sample(target, key, depth + 1)
        if 'default' in schema:
            return schema['default']
        if key in values:
            return values[key]
        if schema.get('enum'):
            return schema['enum'][0]
        for union in ['oneOf', 'anyOf', 'allOf']:
            if schema.get(union):
                return sample(schema[union][0], key, depth + 1)
        kind = schema.get('type')
        if kind == 'object' or 'properties' in schema:
            return {name: sample(field, name, depth + 1) for name, field in schema.get('properties', {}).items()}
        if kind == 'array':
            return [sample(schema['items'], '', depth + 1)]
        if kind == 'integer':
            return 1
        if kind == 'number':
            return 1.0
        if kind == 'boolean':
            return True
        if schema.get('format') == 'date-time':
            return '2026-09-08T12:00:00+08:00'
        return 'Example'

    for path, methods in result.get('paths', {}).items():
        if not path.startswith('/api/v1/'):
            continue
        for method, operation in methods.items():
            if not isinstance(operation, dict) or 'responses' not in operation:
                continue
            resource = path.split('/')[3]
            operation['tags'] = ['Authentication' if resource == 'auth' else resource.replace('-', ' ').title()]
            body = operation.get('requestBody', {}).get('content', {}).get('application/json')
            if body:
                body.setdefault('example', sample(body['schema']))
            for code, response in operation['responses'].items():
                media = response.get('content', {}).get('application/json')
                if media and code.startswith('2'):
                    media.setdefault('example', sample(media['schema']))
    return result
