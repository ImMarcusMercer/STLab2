import re
from datetime import date
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from .models import User, Student, Program, Course, AcademicTerm, CourseOffering, Enrollment, Grade


class StrictModelSerializer(serializers.ModelSerializer):
    """Reject misspelled and read-only input instead of silently discarding it."""
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            readonly = {key for key in data if key in self.fields and self.fields[key].read_only}
            if unknown or readonly:
                raise serializers.ValidationError({key: ['Unknown or read-only field.'] for key in unknown | readonly})
        return super().to_internal_value(data)


class UserSerializer(StrictModelSerializer):
    password = serializers.CharField(write_only=True, required=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_email(self, value):
        value = value.lower()
        matches = User.objects.filter(email__iexact=value)
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate(self, attrs):
        candidate = User(name=attrs.get('name', getattr(self.instance, 'name', '')),
                         email=attrs.get('email', getattr(self.instance, 'email', '')))
        if 'password' in attrs:
            try:
                validate_password(attrs['password'], candidate)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': exc.messages})
        if self.instance:
            role = attrs.get('role', self.instance.role)
            if role != self.instance.role:
                if hasattr(self.instance, 'student') or self.instance.offerings.exists():
                    raise serializers.ValidationError({'role': 'Cannot change the role of a linked student or instructor.'})
            request = self.context.get('request')
            if request and request.user.pk == self.instance.pk:
                if role != 'ADMIN' or not attrs.get('is_active', self.instance.is_active):
                    raise serializers.ValidationError('Administrators cannot deactivate or demote themselves.')
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save()
            instance.auth_token.delete() if hasattr(instance, 'auth_token') else None
        if not instance.is_active:
            instance.auth_token.delete() if hasattr(instance, 'auth_token') else None
        return instance


class ProgramSerializer(StrictModelSerializer):
    class Meta:
        model = Program
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class StudentSerializer(StrictModelSerializer):
    program_id = serializers.PrimaryKeyRelatedField(source='program', queryset=Program.objects.all())
    user_id = serializers.PrimaryKeyRelatedField(source='user', queryset=User.objects.filter(role='STUDENT'),
                                                 required=False, allow_null=True)

    class Meta:
        model = Student
        exclude = ['program', 'user']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_user_id(self, user):
        request = self.context.get('request')
        previous = self.instance.user_id if self.instance else None
        if request and request.user.role != 'ADMIN' and (user.pk if user else None) != previous:
            raise PermissionDenied('Only administrators may link login accounts to student profiles.')
        matches = Student.objects.filter(user=user) if user else Student.objects.none()
        if self.instance:
            matches = matches.exclude(pk=self.instance.pk)
        if matches.exists():
            raise serializers.ValidationError('This user is already linked to a student.')
        return user

    def validate_birth_date(self, value):
        if value and value > date.today():
            raise serializers.ValidationError('Birth date cannot be in the future.')
        return value


class CourseSerializer(StrictModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AcademicTermSerializer(StrictModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_academic_year(self, value):
        if not re.fullmatch(r'\d{4}-\d{4}', value) or int(value[5:]) != int(value[:4]) + 1:
            raise serializers.ValidationError('Use consecutive years, for example 2026-2027.')
        return value

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end < start:
            raise serializers.ValidationError({'end_date': 'Must be on or after start_date.'})
        return attrs


class CourseOfferingSerializer(StrictModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(source='course', queryset=Course.objects.all())
    academic_term_id = serializers.PrimaryKeyRelatedField(source='academic_term', queryset=AcademicTerm.objects.all())
    instructor_id = serializers.PrimaryKeyRelatedField(source='instructor', queryset=User.objects.filter(role='INSTRUCTOR', is_active=True))

    class Meta:
        model = CourseOffering
        exclude = ['course', 'academic_term', 'instructor']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        if self.instance:
            count = self.instance.enrollments.exclude(status='DROPPED').count()
            if attrs.get('capacity', self.instance.capacity) < count:
                raise serializers.ValidationError({'capacity': 'Cannot be below the occupied seat count.'})
            for field in ['course', 'academic_term']:
                if field in attrs and attrs[field].pk != getattr(self.instance, field + '_id') and self.instance.enrollments.exists():
                    raise serializers.ValidationError({field + '_id': 'Cannot change after enrollment.'})
        return attrs


class EnrollmentSerializer(StrictModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(source='student', queryset=Student.objects.all())
    course_offering_id = serializers.PrimaryKeyRelatedField(source='course_offering', queryset=CourseOffering.objects.all())

    class Meta:
        model = Enrollment
        exclude = ['student', 'course_offering']
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']

    def validate(self, attrs):
        if self.instance:
            for field in ['student', 'course_offering']:
                if field in attrs and attrs[field].pk != getattr(self.instance, field + '_id'):
                    raise serializers.ValidationError({field + '_id': 'Enrollment links cannot be changed.'})
            if attrs.get('status') == 'DROPPED' and hasattr(self.instance, 'grade'):
                raise serializers.ValidationError({'status': 'A graded enrollment cannot be dropped.'})
        student = attrs.get('student', getattr(self.instance, 'student', None))
        offering = attrs.get('course_offering', getattr(self.instance, 'course_offering', None))
        status = attrs.get('status', getattr(self.instance, 'status', 'ENROLLED'))
        if status != 'DROPPED' and student and offering:
            if student.status != 'ACTIVE' or offering.status != 'ACTIVE' or offering.academic_term.status != 'ACTIVE':
                raise serializers.ValidationError('Student, offering and academic term must be active.')
            occupied = offering.enrollments.exclude(status='DROPPED')
            if self.instance:
                occupied = occupied.exclude(pk=self.instance.pk)
            if occupied.count() >= offering.capacity:
                raise serializers.ValidationError({'course_offering_id': 'This offering is full.'})
        return attrs


class GradeSerializer(StrictModelSerializer):
    enrollment_id = serializers.PrimaryKeyRelatedField(source='enrollment', queryset=Enrollment.objects.select_related('course_offering').all())

    class Meta:
        model = Grade
        exclude = ['enrollment']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_enrollment_id(self, enrollment):
        request = self.context.get('request')
        if request and request.user.role == 'INSTRUCTOR' and enrollment.course_offering.instructor_id != request.user.id:
            raise PermissionDenied('You may only grade your assigned offerings.')
        return enrollment

    def validate(self, attrs):
        enrollment = attrs.get('enrollment', getattr(self.instance, 'enrollment', None))
        request = self.context.get('request')
        if enrollment and request and request.user.role == 'INSTRUCTOR':
            if enrollment.course_offering.instructor_id != request.user.id:
                raise PermissionDenied('You may only grade your assigned offerings.')
        if self.instance and enrollment.pk != self.instance.enrollment_id:
            raise serializers.ValidationError({'enrollment_id': 'Cannot move a grade to another enrollment.'})
        if enrollment and enrollment.status == 'DROPPED':
            raise serializers.ValidationError({'enrollment_id': 'Cannot grade a dropped enrollment.'})
        final = attrs.get('final_grade', getattr(self.instance, 'final_grade', None))
        status = attrs.get('status', getattr(self.instance, 'status', 'DRAFT'))
        if status == 'FINALIZED' and final is None:
            raise serializers.ValidationError({'final_grade': 'A finalized grade requires a final rating.'})
        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField()
    expires_at = serializers.DateTimeField()
    user = UserSerializer(read_only=True)


class AcademicRecordEntrySerializer(serializers.Serializer):
    enrollment = EnrollmentSerializer()
    course = CourseSerializer()
    grade = GradeSerializer(allow_null=True)


class TermRecordSerializer(serializers.Serializer):
    term = AcademicTermSerializer()
    records = AcademicRecordEntrySerializer(many=True)


class AcademicRecordSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    terms = TermRecordSerializer(many=True)
    pagination = serializers.DictField()
