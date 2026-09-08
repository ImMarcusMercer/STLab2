from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if token.created + timedelta(hours=settings.TOKEN_TTL_HOURS) <= timezone.now():
            token.delete()
            raise AuthenticationFailed('Token expired. Log in again.')
        return user, token


class TokenScheme(OpenApiAuthenticationExtension):
    target_class = ExpiringTokenAuthentication
    name = 'tokenAuth'

    def get_security_definition(self, auto_schema):
        return {'type': 'apiKey', 'in': 'header', 'name': 'Authorization',
                'description': 'Enter Token followed by a space and your login token.'}
