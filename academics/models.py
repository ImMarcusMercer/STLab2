from decimal import Decimal

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.update(is_staff=True, is_superuser=True, role='ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        REGISTRAR = 'REGISTRAR', 'Registrar / Staff'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        STUDENT = 'STUDENT', 'Student'

    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    objects = UserManager()


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['id']


class Status(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'


class Program(Timestamped):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)


class Student(Timestamped):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='student', null=True, blank=True)
    student_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, db_index=True)
    suffix = models.CharField(max_length=15, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name='students')
    year_level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta(Timestamped.Meta):
        constraints = [models.CheckConstraint(condition=Q(year_level__gte=1, year_level__lte=6), name='student_year_1_6')]

    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name, self.suffix]
        return ' '.join(p for p in parts if p)

    def __str__(self):
        return f'{self.student_number} {self.full_name()}'


class Course(Timestamped):
    course_code = models.CharField(max_length=20, unique=True)
    course_title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    units = models.DecimalField(max_digits=4, decimal_places=1, validators=[MinValueValidator(Decimal('0.5')), MaxValueValidator(Decimal('12'))])
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    def __str__(self):
        return f'{self.course_code} {self.course_title}'

    class Meta(Timestamped.Meta):
        constraints = [models.CheckConstraint(condition=Q(units__gte=0.5, units__lte=12), name='course_units_range')]


class AcademicTerm(Timestamped):
    academic_year = models.CharField(max_length=9)
    semester = models.CharField(max_length=6, choices=[('FIRST', 'First'), ('SECOND', 'Second'), ('SUMMER', 'Summer')])
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    def __str__(self):
        return f'{self.academic_year} {self.get_semester_display()}'

    class Meta(Timestamped.Meta):
        constraints = [models.UniqueConstraint(fields=['academic_year', 'semester'], name='unique_year_semester'),
                       models.CheckConstraint(condition=Q(end_date__gte=models.F('start_date')), name='term_dates_ordered')]


class CourseOffering(Timestamped):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='offerings')
    academic_term = models.ForeignKey(AcademicTerm, on_delete=models.PROTECT, related_name='offerings')
    instructor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='offerings')
    section = models.CharField(max_length=30)
    schedule = models.CharField(max_length=150)
    room = models.CharField(max_length=50, blank=True)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(1000)])
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)

    class Meta(Timestamped.Meta):
        constraints = [models.UniqueConstraint(fields=['course', 'academic_term', 'section'], name='unique_offering_section'),
                       models.CheckConstraint(condition=Q(capacity__gte=1, capacity__lte=1000), name='offering_capacity_range')]


class Enrollment(Timestamped):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='enrollments')
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=[('ENROLLED', 'Enrolled'), ('DROPPED', 'Dropped'),
                                                     ('COMPLETED', 'Completed')], default='ENROLLED')

    class Meta(Timestamped.Meta):
        constraints = [models.UniqueConstraint(fields=['student', 'course_offering'], name='unique_student_offering')]


class Grade(Timestamped):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.PROTECT, related_name='grade')
    midterm_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    remarks = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=9, choices=[('DRAFT', 'Draft'), ('FINALIZED', 'Finalized')], default='DRAFT')

    class Meta(Timestamped.Meta):
        constraints = [models.CheckConstraint(condition=Q(midterm_grade__isnull=True) | Q(midterm_grade__gte=0, midterm_grade__lte=100), name='midterm_range'),
                       models.CheckConstraint(condition=Q(final_grade__isnull=True) | Q(final_grade__gte=0, final_grade__lte=100), name='final_range'),
                       models.CheckConstraint(condition=~Q(status='FINALIZED') | Q(final_grade__isnull=False), name='finalized_has_rating')]
