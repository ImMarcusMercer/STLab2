import json
import requests
import pytest
from src.api.client import ApiClient, ApiError


class Response:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload
        self.content = b'' if payload is None else json.dumps(payload).encode()

    def json(self): return self._payload


class Session:
    def __init__(self, responses): self.responses = list(responses); self.calls = []
    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return response


def test_login_stores_token_in_memory_and_sends_it():
    http = Session([Response(200, {'data': {'token': 'secret', 'user': {'id': 1, 'role': 'ADMIN'}}}),
                    Response(200, {'count': 0, 'results': []})])
    api = ApiClient('http://example.test/api/v1', session=http)
    assert api.login('admin@example.test', 'password')['role'] == 'ADMIN'
    api.list('students', search='Ana')
    assert api.authenticated
    assert http.calls[1][1]['headers']['Authorization'] == 'Token secret'
    assert http.calls[1][1]['params']['search'] == 'Ana'


def test_204_has_no_json_and_logout_clears_auth():
    api = ApiClient('http://example.test', session=Session([Response(204)]))
    api.token, api.user = 'token', {'role': 'ADMIN'}
    assert api.logout() is None
    assert not api.authenticated


def test_validation_error_normalizes_field_messages():
    api = ApiClient('http://example.test', session=Session([Response(422, {
        'message': 'Validation failed.', 'errors': {'email': ['Enter a valid email address.']}})]))
    with pytest.raises(ApiError) as caught: api.create('students', {'email': 'bad'})
    assert caught.value.status == 422
    assert caught.value.field_messages['email'] == 'Enter a valid email address.'


def test_401_clears_authentication():
    api = ApiClient('http://example.test', session=Session([Response(401, {'message': 'Expired', 'errors': {}})]))
    api.token, api.user = 'expired', {'role': 'STUDENT'}
    with pytest.raises(ApiError): api.list('students')
    assert not api.authenticated


@pytest.mark.parametrize('failure', [requests.Timeout(), requests.ConnectionError()])
def test_network_failure_becomes_actionable_error(failure):
    api = ApiClient('http://example.test', session=Session([failure]))
    with pytest.raises(ApiError) as caught: api.list('students')
    assert caught.value.kind == 'network'
    assert 'backend is running' in caught.value.message


def test_403_404_409_and_500_have_safe_fallback_messages():
    for status, phrase in [(403, 'permission'), (404, 'not found'), (409, 'conflicts'), (500, 'retry')]:
        api = ApiClient('http://example.test', session=Session([Response(status)]))
        with pytest.raises(ApiError) as caught: api.list('students')
        assert phrase in caught.value.message.lower()
