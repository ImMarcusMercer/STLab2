import logging
from django.db import IntegrityError, OperationalError
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class Pagination(PageNumberPagination):
    page_size_query_param = 'per_page'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        for field in ['page', 'per_page']:
            value = request.query_params.get(field)
            if value is not None and (not value.isdigit() or int(value) < 1):
                raise ValidationError({field: ['Must be a positive integer.']})
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return Response({'count': self.page.paginator.count, 'next': self.get_next_link(),
                         'previous': self.get_previous_link(), 'page': self.page.number,
                         'per_page': self.page.paginator.per_page,
                         'last_page': self.page.paginator.num_pages, 'results': data})

    def get_paginated_response_schema(self, schema):
        result = super().get_paginated_response_schema(schema)
        result['properties'].update({key: {'type': 'integer'} for key in ['page', 'per_page', 'last_page']})
        return result


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if isinstance(exc, ProtectedError):
        return Response({'success': False, 'message': 'Resource is referenced by other records. Deactivate it instead.', 'errors': {}}, status=409)
    if isinstance(exc, IntegrityError):
        return Response({'success': False, 'message': 'A uniqueness or relationship constraint conflicts with this request.', 'errors': {}}, status=409)
    if isinstance(exc, OperationalError):
        logger.error('Database operation failed (%s).', type(exc).__name__)
        return Response({'success': False, 'message': 'Database temporarily unavailable. Retry the request.', 'errors': {}}, status=503)
    if response is not None:
        if isinstance(exc, ValidationError):
            response.status_code = 422
        message = 'Validation failed.' if response.status_code == 422 else str(response.data.get('detail', 'Request failed.')) if isinstance(response.data, dict) else 'Request failed.'
        response.data = {'success': False, 'message': message, 'errors': response.data}
        return response
    # Do not log exception messages or request bodies, which can contain credentials.
    logger.error('Unhandled API exception: %s', type(exc).__name__)
    return Response({'success': False, 'message': 'Internal server error.', 'errors': {}}, status=500)


def not_found(request, exception=None):
    return JsonResponse({'success': False, 'message': 'Not found.', 'errors': {}}, status=404)


def server_error(request):
    return JsonResponse({'success': False, 'message': 'Internal server error.', 'errors': {}}, status=500)
