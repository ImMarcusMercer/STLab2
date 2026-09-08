from datetime import timedelta
from django.conf import settings
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .models import AcademicTerm, Course, CourseOffering, Enrollment, Grade, Program, Student, User
from .serializers import (CourseOfferingSerializer, CourseSerializer, EnrollmentSerializer,
                          GradeSerializer, LoginSerializer, ProgramSerializer, StudentSerializer,
                          TermRecordSerializer, AcademicTermSerializer, UserSerializer,
                          TokenSerializer)


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


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminOnly]
    filterset_fields = ['role', 'is_active']
    search_fields = ['name', 'email']


class ProgramViewSet(viewsets.ModelViewSet):
    queryset = Program.objects.all()
    serializer_class = ProgramSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['status']
    search_fields = ['code', 'name']
    ordering_fields = ['code', 'name', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['status']
    search_fields = ['course_code', 'course_title']
    ordering_fields = ['course_code', 'course_title', 'units', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


class AcademicTermViewSet(viewsets.ModelViewSet):
    queryset = AcademicTerm.objects.all()
    serializer_class = AcademicTermSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['academic_year', 'semester', 'status']
    search_fields = ['academic_year']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']


class CourseOfferingViewSet(viewsets.ModelViewSet):
    queryset = CourseOffering.objects.select_related('course', 'academic_term', 'instructor')
    serializer_class = CourseOfferingSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['course', 'academic_term', 'instructor', 'status', 'section']
    search_fields = ['course__course_code', 'course__course_title', 'section', 'room']
    ordering_fields = ['section', 'schedule', 'capacity', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_instructor(user):
            qs = qs.filter(instructor=user)
        return qs

    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        if _is_student(request.user):
            raise PermissionDenied('Students cannot view enrollment rosters.')
        offering = self.get_object()
        enrollments = offering.enrollments.select_related('student').filter(status__in=['ENROLLED', 'COMPLETED'])
        students = [e.student for e in enrollments]
        return Response({
            'success': True,
            'message': 'Enrolled students retrieved.',
            'data': [{'id': s.id, 'student_number': s.student_number,
                      'full_name': s.full_name(), 'year_level': s.year_level,
                      'program': s.program.code if s.program else None} for s in students],
        })


class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.select_related('student', 'course_offering')
    serializer_class = EnrollmentSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['student', 'course_offering', 'status']
    search_fields = ['student__student_number', 'student__last_name',
                     'course_offering__section', 'course_offering__course__course_code']
    ordering_fields = ['enrollment_date', 'created_at']
    http_method_names = ['get', 'post', 'patch', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_instructor(user):
            qs = qs.filter(course_offering__instructor=user)
        elif _is_student(user):
            qs = qs.filter(student__user=user)
        return qs


class GradeViewSet(viewsets.ModelViewSet):
    queryset = Grade.objects.select_related('enrollment__student', 'enrollment__course_offering')
    serializer_class = GradeSerializer
    permission_classes = [IsStaffOrInstructorGradeEditor]
    filterset_fields = ['enrollment', 'status']
    search_fields = ['enrollment__student__student_number', 'enrollment__student__last_name',
                     'enrollment__course_offering__section']
    ordering_fields = ['midterm_grade', 'final_grade', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_instructor(user):
            return qs.filter(enrollment__course_offering__instructor=user)
        if _is_student(user):
            return qs.filter(enrollment__student__user=user)
        return qs


class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.select_related('program', 'user').all()
    serializer_class = StudentSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ['program', 'year_level', 'status']
    search_fields = ['student_number', 'first_name', 'last_name', 'email']
    ordering_fields = ['student_number', 'last_name', 'year_level', 'created_at']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if _is_student(user):
            return qs.filter(user=user)
        if _is_instructor(user):
            return qs.filter(enrollments__course_offering__instructor=user).distinct()
        return qs

    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        student = self.get_object()
        enrollments = student.enrollments.select_related('course_offering__course',
                                                          'course_offering__academic_term').all()
        data = [{
            'id': e.id,
            'status': e.status,
            'enrollment_date': e.enrollment_date,
            'course': e.course_offering.course.course_code,
            'course_title': e.course_offering.course.course_title,
            'term': str(e.course_offering.academic_term),
            'section': e.course_offering.section,
        } for e in enrollments]
        return Response({'success': True, 'message': 'Enrollments retrieved.', 'data': data})

    @action(detail=True, methods=['get'])
    def grades(self, request, pk=None):
        student = self.get_object()
        enrollments = student.enrollments.select_related('grade', 'course_offering__course',
                                                          'course_offering__academic_term').all()
        data = []
        for e in enrollments:
            g = getattr(e, 'grade', None)
            if not g:
                continue
            data.append({
                'id': g.id,
                'course': e.course_offering.course.course_code,
                'course_title': e.course_offering.course.course_title,
                'semester': e.course_offering.academic_term.semester,
                'midterm_grade': g.midterm_grade,
                'final_grade': g.final_grade,
                'remarks': g.remarks,
            })
        return Response({'success': True, 'message': 'Grades retrieved.', 'data': data})

    @action(detail=True, methods=['get'], url_path='academic-record')
    def academic_record(self, request, pk=None):
        student = self.get_object()
        enrolled = student.enrollments.select_related('grade', 'course_offering__course',
                                                       'course_offering__academic_term').all()
        terms = {}
        for e in enrolled:
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
            'data': {'student_id': student.id, 'terms': term_records},
        })


class AuthView(APIView):
    permission_classes = []
    serializer_class = LoginSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    @extend_schema(request=LoginSerializer, responses={200: TokenSerializer}, tags=['Authentication'],
                   summary='Authenticate and receive a token',
                   description='Returns a token valid for the configured TTL. Send it as `Authorization: Token <key>`.')
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email'].lower()
        password = serializer.validated_data['password']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = None
        if user is None or not user.check_password(password):
            raise AuthenticationFailed('Invalid email or password.')
        if not user.is_active:
            raise AuthenticationFailed('This account is deactivated.')
        token, _ = Token.objects.get_or_create(user=user)
        expires_at = token.created + timedelta(hours=settings.TOKEN_TTL_HOURS)
        payload = TokenSerializer({'token': token.key, 'expires_at': expires_at, 'user': user}).data
        return Response({'success': True, 'message': 'Login successful.', 'data': payload})


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(request=None, responses={200: UserSerializer}, tags=['Authentication'],
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
        return Response({'success': True, 'message': 'Logged out.', 'data': None}, status=204)
