from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers
from .filters import StudentFilter, OfferingFilter, EnrollmentFilter, GradeFilter

from .models import AcademicTerm, Course, CourseOffering, Enrollment, Grade, Program, Student, User
from .serializers import (CourseOfferingSerializer, CourseSerializer, EnrollmentSerializer,
                          GradeSerializer, LoginSerializer, ProgramSerializer, StudentSerializer,
                          TermRecordSerializer, AcademicTermSerializer, UserSerializer,
                          TokenSerializer, AcademicRecordSerializer)


def envelope(name, serializer):
    return inline_serializer(name, fields={'success': serializers.BooleanField(),
                                          'message': serializers.CharField(), 'data': serializer})


class AtomicViewSet(viewsets.ModelViewSet):
    """Keep validation and persistence in one SQLite IMMEDIATE transaction.

    This serializes writers before capacity checks and prevents over-enrollment.
    Reads do not acquire a write lock.
    """
    @method_decorator(transaction.atomic)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @method_decorator(transaction.atomic)
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @method_decorator(transaction.atomic)
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


def _is_admin(user):
    return user.role == User.Role.ADMIN


def _is_registrar(user):
    return user.role == User.Role.REGISTRAR


def _is_instructor(user):
    return user.role == User.Role.INSTRUCTOR


def _is_student(user):
    return user.role == User.Role.STUDENT


class IsStaffOrReadOnly(IsAuthenticated):
    """Admin/Registrar may write; any authenticated user may read."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return _is_admin(request.user) or _is_registrar(request.user)


class IsRegistrarOrAdmin(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _is_admin(request.user) or _is_registrar(request.user)


class IsStaffOrInstructorGradeEditor(IsAuthenticated):
    """Anyone authenticated may read grades; admin/registrar/instructor may write.
    Instructors are restricted to their own offerings by the serializer."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return _is_admin(request.user) or _is_registrar(request.user) or _is_instructor(request.user)


class IsAdminOnly(IsAuthenticated):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and _is_admin(request.user)


class UserViewSet(AtomicViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminOnly]
    filterset_fields = ['role', 'is_active']
    search_fields = ['name', 'email']
    ordering_fields = ['id', 'name', 'email', 'created_at']

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise PermissionDenied('Administrators cannot delete themselves.')
        instance.delete()


class ProgramViewSet(AtomicViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['status']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


class CourseViewSet(AtomicViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['status']
    search_fields = ['course_code', 'course_title']
    ordering_fields = ['course_code', 'course_title', 'units', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


class AcademicTermViewSet(AtomicViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['academic_year', 'semester', 'status']
    search_fields = ['academic_year']
    ordering_fields = ['academic_year', 'start_date', 'end_date', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


class CourseOfferingViewSet(AtomicViewSet):
    queryset = CourseOffering.objects.select_related('course', 'academic_term', 'instructor')
    serializer_class = CourseOfferingSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = OfferingFilter
    search_fields = ['course__course_code', 'course__course_title', 'section', 'room']
    ordering_fields = ['section', 'schedule', 'capacity', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        user = self.request.user
        if _is_instructor(user):
            qs = qs.filter(instructor=user)
        return qs

    @extend_schema(responses=inline_serializer('RosterStudent', fields={
        'id': serializers.IntegerField(), 'student_number': serializers.CharField(),
        'full_name': serializers.CharField(), 'year_level': serializers.IntegerField(),
        'program': serializers.CharField()}, many=True))
    @action(detail=True, methods=['get'], filter_backends=[])
    def students(self, request, pk=None):
        if _is_student(request.user):
            raise PermissionDenied('Students cannot view enrollment rosters.')
        offering = self.get_object()
        enrollments = offering.enrollments.select_related('student__program').filter(status__in=['ENROLLED', 'COMPLETED'])
        students = [e.student for e in self.paginate_queryset(enrollments)]
        return self.get_paginated_response([{'id': s.id, 'student_number': s.student_number,
                      'full_name': s.full_name(), 'year_level': s.year_level,
                      'program': s.program.code} for s in students])


class EnrollmentViewSet(AtomicViewSet):
    queryset = Enrollment.objects.select_related('student', 'course_offering')
    serializer_class = EnrollmentSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = EnrollmentFilter
    search_fields = ['student__student_number', 'student__last_name',
                     'course_offering__section', 'course_offering__course__course_code']
    ordering_fields = ['enrollment_date', 'created_at']
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        user = self.request.user
        if _is_instructor(user):
            qs = qs.filter(course_offering__instructor=user)
        elif _is_student(user):
            qs = qs.filter(student__user=user)
        return qs


class GradeViewSet(AtomicViewSet):
    queryset = Grade.objects.select_related('enrollment__student', 'enrollment__course_offering')
    serializer_class = GradeSerializer
    permission_classes = [IsStaffOrInstructorGradeEditor]
    filterset_class = GradeFilter
    search_fields = ['enrollment__student__student_number', 'enrollment__student__last_name',
                     'enrollment__course_offering__section']
    ordering_fields = ['midterm_grade', 'final_grade', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch']

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        user = self.request.user
        if _is_instructor(user):
            return qs.filter(enrollment__course_offering__instructor=user)
        if _is_student(user):
            return qs.filter(enrollment__student__user=user)
        return qs


class StudentViewSet(AtomicViewSet):
    queryset = Student.objects.select_related('program', 'user').all()
    serializer_class = StudentSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_class = StudentFilter
    search_fields = ['student_number', 'first_name', 'last_name', 'email']
    ordering_fields = ['student_number', 'last_name', 'year_level', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def check_permissions(self, request):
        super().check_permissions(request)
        if _is_instructor(request.user):
            raise PermissionDenied('Use assigned offering rosters, enrollments and grades. Full student records are restricted.')

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        user = self.request.user
        if _is_student(user):
            return qs.filter(user=user)
        if _is_instructor(user):
            return qs.filter(enrollments__course_offering__instructor=user).distinct()
        return qs

    @extend_schema(responses=EnrollmentSerializer(many=True))
    @action(detail=True, methods=['get'], filter_backends=[])
    def enrollments(self, request, pk=None):
        student = self.get_object()
        enrollments = student.enrollments.select_related('course_offering__course',
                                                          'course_offering__academic_term').all()
        return self.get_paginated_response(EnrollmentSerializer(self.paginate_queryset(enrollments), many=True).data)

    @extend_schema(responses=GradeSerializer(many=True))
    @action(detail=True, methods=['get'], filter_backends=[])
    def grades(self, request, pk=None):
        student = self.get_object()
        grades = Grade.objects.filter(enrollment__student=student)
        return self.get_paginated_response(GradeSerializer(self.paginate_queryset(grades), many=True).data)

    @extend_schema(responses=envelope('AcademicRecordResponse', AcademicRecordSerializer()),
                   parameters=[OpenApiParameter('page', int), OpenApiParameter('per_page', int)],
                   description='Student or staff only. Enrollment rows are paginated, then grouped by term; follow pagination.next for all records.')
    @action(detail=True, methods=['get'], url_path='academic-record', filter_backends=[])
    def academic_record(self, request, pk=None):
        student = self.get_object()
        enrolled = student.enrollments.select_related('grade', 'course_offering__course',
                                                       'course_offering__academic_term').all()
        terms = {}
        for e in self.paginate_queryset(enrolled.order_by('course_offering__academic_term__start_date', 'id')):
            term = e.course_offering.academic_term
            terms.setdefault(term.id, {'term': term, 'records': []})
            entry = {'enrollment': e, 'course': e.course_offering.course,
                     'grade': getattr(e, 'grade', None)}
            terms[term.id]['records'].append(entry)

        term_records = []
        for term_data in sorted(terms.values(), key=lambda t: (t['term'].start_date, t['term'].id)):
            term_records.append(TermRecordSerializer({
                'term': term_data['term'],
                'records': term_data['records'],
            }).data)
        return Response({
            'success': True,
            'message': 'Academic record retrieved.',
            'data': {'student_id': student.id, 'terms': term_records,
                     'pagination': {key: value for key, value in self.get_paginated_response([]).data.items() if key != 'results'}},
        })


class AuthView(APIView):
    permission_classes = []
    authentication_classes = []
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    @extend_schema(request=LoginSerializer, responses={200: envelope('LoginResponse', TokenSerializer())}, tags=['Authentication'], auth=[],
                   summary='Authenticate and receive a token',
                   description='Returns a token valid for the configured TTL. Send it as `Authorization: Token <key>`.')
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        # Django runs a dummy password hash for an unknown account and rejects inactive users.
        user = authenticate(request=request, email=email, password=password)
        if user is None:
            raise AuthenticationFailed('Invalid email or password.')
        with transaction.atomic():
            Token.objects.filter(user=user, created__lte=timezone.now() - timedelta(hours=settings.TOKEN_TTL_HOURS)).delete()
            token, _ = Token.objects.get_or_create(user=user)
        expires_at = token.created + timedelta(hours=settings.TOKEN_TTL_HOURS)
        payload = TokenSerializer({'token': token.key, 'expires_at': expires_at, 'user': user}).data
        return Response({'success': True, 'message': 'Login successful.', 'data': payload})

    def get_authenticate_header(self, request):
        return 'Token'


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(request=None, responses={200: envelope('MeResponse', UserSerializer())}, tags=['Authentication'],
                   summary='Current authenticated user')
    def get(self, request):
        return Response({
            'success': True,
            'message': 'Current user retrieved.',
            'data': UserSerializer(request.user).data,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None}, tags=['Authentication'],
                   summary='Logout and invalidate the current token')
    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=204)
