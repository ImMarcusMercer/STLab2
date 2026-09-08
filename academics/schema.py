_ERROR_SCHEMA = {
    'type': 'object',
    'properties': {
        'success': {'type': 'boolean', 'enum': [False]},
        'message': {'type': 'string'},
        'errors': {
            'type': 'object',
            'additionalProperties': {'type': 'array', 'items': {'type': 'string'}},
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
    422: ('Validation Failed', {'success': False, 'message': 'Validation failed.',
                                'errors': {'email': ['A valid email address is required.']}}),
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
            responses = operation.setdefault('responses', {})
            for code in _ERRORS:
                responses[str(code)] = _error_response(code)
    return result