from dataclasses import dataclass, field
from typing import Any, Callable
import requests


@dataclass
class ApiError(Exception):
    status: int | None
    message: str
    errors: dict[str, list[str]] = field(default_factory=dict)
    kind: str = 'api'

    def __str__(self):
        return self.message

    @property
    def field_messages(self):
        result = {}
        for key, values in self.errors.items():
            if isinstance(values, list):
                result[key] = '\n'.join(str(value) for value in values)
            elif isinstance(values, dict):
                result[key] = '\n'.join(f'{name}: {value}' for name, value in values.items())
            else:
                result[key] = str(values)
        return result


class ApiClient:
    """The only HTTP boundary used by the frontend; it never accesses the database."""
    def __init__(self, base_url: str, timeout: float = 15, session=None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.http = session or requests.Session()
        self.token: str | None = None
        self.user: dict[str, Any] | None = None
        self.on_unauthorized: Callable[[], None] | None = None

    @property
    def authenticated(self):
        return bool(self.token and self.user)

    def clear_auth(self):
        self.token = None
        self.user = None

    def request(self, method: str, path: str, *, params=None, json=None):
        headers = {'Accept': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Token {self.token}'
        try:
            response = self.http.request(method, self.base_url + '/' + path.lstrip('/'),
                                         params=params, json=json, headers=headers, timeout=self.timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise ApiError(None, 'The API server is unreachable. Check that the backend is running, then retry.', kind='network') from exc
        except requests.RequestException as exc:
            raise ApiError(None, 'The request could not be completed.', kind='network') from exc
        payload = None
        if response.content:
            try:
                payload = response.json()
            except ValueError:
                payload = None
        if 200 <= response.status_code < 300:
            return payload
        if response.status_code == 401 and self.token:
            self.clear_auth()
            if self.on_unauthorized:
                self.on_unauthorized()
        default = {
            400: 'The request is malformed.', 401: 'Your session is missing or expired. Please sign in again.',
            403: 'You do not have permission to perform this action.', 404: 'The requested record was not found.',
            409: 'The request conflicts with existing data.', 422: 'Please correct the highlighted fields.',
            429: 'Too many requests. Wait a moment and try again.',
        }.get(response.status_code, 'The server could not complete the request. Please retry.')
        message = payload.get('message', default) if isinstance(payload, dict) else default
        errors = payload.get('errors', {}) if isinstance(payload, dict) else {}
        if isinstance(errors, dict) and 'detail' in errors and not message:
            message = str(errors['detail'])
        raise ApiError(response.status_code, message, errors if isinstance(errors, dict) else {},
                       kind='server' if response.status_code >= 500 else 'api')

    def login(self, email, password):
        result = self.request('POST', 'auth/login', json={'email': email, 'password': password})
        data = result['data']
        self.token, self.user = data['token'], data['user']
        return self.user

    def restore(self):
        result = self.request('GET', 'auth/me')
        self.user = result['data']
        return self.user

    def logout(self):
        try:
            if self.token:
                self.request('POST', 'auth/logout')
        finally:
            self.clear_auth()

    def list(self, resource, **params):
        return self.request('GET', resource, params={k: v for k, v in params.items() if v not in ('', None)})

    def get(self, resource, record_id):
        return self.request('GET', f'{resource}/{record_id}')

    def create(self, resource, data):
        return self.request('POST', resource, json=data)

    def update(self, resource, record_id, data):
        return self.request('PATCH', f'{resource}/{record_id}', json=data)

    def delete(self, resource, record_id):
        return self.request('DELETE', f'{resource}/{record_id}')
