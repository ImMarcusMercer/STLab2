from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AcademicTermViewSet, AuthView, CourseOfferingViewSet, CourseViewSet,
                    EnrollmentViewSet, GradeViewSet, LogoutView, MeView, ProgramViewSet,
                    StudentViewSet, UserViewSet)

router = DefaultRouter()
router.trailing_slash = ''
router.register('users', UserViewSet)
router.register('programs', ProgramViewSet)
router.register('courses', CourseViewSet)
router.register('academic-terms', AcademicTermViewSet)
router.register('course-offerings', CourseOfferingViewSet)
router.register('enrollments', EnrollmentViewSet)
router.register('grades', GradeViewSet)
router.register('students', StudentViewSet)

urlpatterns = [
    path('auth/login', AuthView.as_view(), name='auth-login'),
    path('auth/logout', LogoutView.as_view(), name='auth-logout'),
    path('auth/me', MeView.as_view(), name='auth-me'),
    path('', include(router.urls)),
]
