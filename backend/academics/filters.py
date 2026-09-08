import django_filters as filters
from rest_framework.filters import OrderingFilter
from rest_framework.exceptions import ValidationError
from .models import Student, CourseOffering, Enrollment, Grade


class StudentFilter(filters.FilterSet):
    program_id = filters.NumberFilter(field_name='program_id')

    class Meta:
        model = Student
        fields = ['program_id', 'year_level', 'status']


class OfferingFilter(filters.FilterSet):
    course_id = filters.NumberFilter(field_name='course_id')
    academic_term_id = filters.NumberFilter(field_name='academic_term_id')
    instructor_id = filters.NumberFilter(field_name='instructor_id')

    class Meta:
        model = CourseOffering
        fields = ['course_id', 'academic_term_id', 'instructor_id', 'section', 'status']


class EnrollmentFilter(filters.FilterSet):
    student_id = filters.NumberFilter(field_name='student_id')
    course_offering_id = filters.NumberFilter(field_name='course_offering_id')

    class Meta:
        model = Enrollment
        fields = ['student_id', 'course_offering_id', 'status']


class GradeFilter(filters.FilterSet):
    enrollment_id = filters.NumberFilter(field_name='enrollment_id')

    class Meta:
        model = Grade
        fields = ['enrollment_id', 'status']


class StableOrderingFilter(OrderingFilter):
    """Allowlisted ordering with a unique tie breaker for repeatable pages."""
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        requested = request.query_params.get(self.ordering_param)
        if requested:
            allowed = {field[0] for field in self.get_valid_fields(queryset, view, {'request': request})}
            if any(part.strip().lstrip('-') not in allowed for part in requested.split(',')):
                raise ValidationError({'sort': ['Unsupported sort field. See the endpoint documentation.']})
        ordering = list(ordering or queryset.query.order_by or queryset.model._meta.ordering or ['id'])
        if not any(field.lstrip('-') in ('id', 'pk') for field in ordering):
            ordering.append('id')
        return ordering
