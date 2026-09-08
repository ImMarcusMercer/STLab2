from dataclasses import dataclass, field


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = 'text'
    required: bool = False
    choices: tuple = ()
    reference: str = ''


@dataclass(frozen=True)
class Resource:
    key: str
    title: str
    columns: tuple
    fields: tuple[Field, ...]
    search: bool = True
    filters: tuple = ()
    sorts: tuple = ()
    write_roles: tuple = ('ADMIN', 'REGISTRAR')
    delete: bool = True
    endpoint: str = ''

    @property
    def path(self):
        return self.endpoint or self.key


STATUS = (('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'))
RESOURCES = {
    'users': Resource('users', 'Users', (('name', 'Name'), ('email', 'Email'), ('role', 'Role'), ('is_active', 'Active')),
        (Field('name', 'Name', required=True), Field('email', 'Email', 'email', True), Field('password', 'Password', 'password', True),
         Field('role', 'Role', 'choice', True, (('ADMIN', 'Administrator'), ('REGISTRAR', 'Registrar'), ('INSTRUCTOR', 'Instructor'), ('STUDENT', 'Student'))),
         Field('is_active', 'Active', 'choice', choices=((True, 'Active'), (False, 'Inactive')))),
        filters=(('role', 'Role', (('ADMIN', 'Administrator'), ('REGISTRAR', 'Registrar'), ('INSTRUCTOR', 'Instructor'), ('STUDENT', 'Student'))),
                 ('is_active', 'Status', ((True, 'Active'), (False, 'Inactive')))), sorts=(('name', 'Name'), ('email', 'Email')), write_roles=('ADMIN',)),
    'students': Resource('students', 'Students',
        (('student_number', 'Student #'), ('last_name', 'Last name'), ('first_name', 'First name'), ('program_id', 'Program'), ('year_level', 'Year'), ('status', 'Status')),
        (Field('student_number', 'Student number', required=True), Field('first_name', 'First name', required=True),
         Field('middle_name', 'Middle name'), Field('last_name', 'Last name', required=True), Field('suffix', 'Suffix'),
         Field('birth_date', 'Birth date', 'date'), Field('email', 'Email', 'email'), Field('contact_number', 'Contact number'),
         Field('address', 'Address', 'multiline'), Field('program_id', 'Program', 'ref', True, reference='programs'),
         Field('year_level', 'Year level', 'int', True, choices=tuple((str(i), str(i)) for i in range(1, 7))),
         Field('status', 'Status', 'choice', choices=STATUS)),
        filters=(('program_id', 'Program', 'programs'), ('year_level', 'Year level', tuple(str(i) for i in range(1, 7))), ('status', 'Status', STATUS)),
        sorts=(('last_name', 'Last name'), ('student_number', 'Student number'), ('year_level', 'Year level'))),
    'programs': Resource('programs', 'Programs', (('code', 'Code'), ('name', 'Name'), ('description', 'Description'), ('status', 'Status')),
        (Field('code', 'Code', required=True), Field('name', 'Name', required=True), Field('description', 'Description', 'multiline'), Field('status', 'Status', 'choice', choices=STATUS)),
        filters=(('status', 'Status', STATUS),), sorts=(('code', 'Code'), ('name', 'Name'))),
    'courses': Resource('courses', 'Courses', (('course_code', 'Code'), ('course_title', 'Title'), ('units', 'Units'), ('status', 'Status')),
        (Field('course_code', 'Course code', required=True), Field('course_title', 'Title', required=True), Field('description', 'Description', 'multiline'), Field('units', 'Units', 'decimal', True), Field('status', 'Status', 'choice', choices=STATUS)),
        filters=(('status', 'Status', STATUS),), sorts=(('course_code', 'Code'), ('course_title', 'Title'), ('units', 'Units'))),
    'academic-terms': Resource('academic-terms', 'Academic Terms', (('academic_year', 'Academic year'), ('semester', 'Semester'), ('start_date', 'Start'), ('end_date', 'End'), ('status', 'Status')),
        (Field('academic_year', 'Academic year', required=True), Field('semester', 'Semester', 'choice', True, (('FIRST', 'First'), ('SECOND', 'Second'), ('SUMMER', 'Summer'))), Field('start_date', 'Start date', 'date', True), Field('end_date', 'End date', 'date', True), Field('status', 'Status', 'choice', choices=STATUS)),
        filters=(('semester', 'Semester', (('FIRST', 'First'), ('SECOND', 'Second'), ('SUMMER', 'Summer'))), ('status', 'Status', STATUS)), sorts=(('academic_year', 'Academic year'), ('start_date', 'Start date'))),
    'course-offerings': Resource('course-offerings', 'Course Offerings', (('course_id', 'Course'), ('academic_term_id', 'Term'), ('instructor_id', 'Instructor'), ('section', 'Section'), ('schedule', 'Schedule'), ('capacity', 'Capacity'), ('status', 'Status')),
        (Field('course_id', 'Course', 'ref', True, reference='courses'), Field('academic_term_id', 'Academic term', 'ref', True, reference='academic-terms'), Field('instructor_id', 'Instructor', 'ref', True, reference='users?role=INSTRUCTOR'), Field('section', 'Section', required=True), Field('schedule', 'Schedule', required=True), Field('room', 'Room'), Field('capacity', 'Capacity', 'int', True), Field('status', 'Status', 'choice', choices=STATUS)),
        filters=(('course_id', 'Course', 'courses'), ('academic_term_id', 'Term', 'academic-terms'), ('instructor_id', 'Instructor', 'users?role=INSTRUCTOR'), ('status', 'Status', STATUS)), sorts=(('section', 'Section'), ('schedule', 'Schedule'), ('capacity', 'Capacity'))),
    'enrollments': Resource('enrollments', 'Enrollments', (('student_id', 'Student'), ('course_offering_id', 'Offering'), ('enrollment_date', 'Date'), ('status', 'Status')),
        (Field('student_id', 'Student', 'ref', True, reference='students'), Field('course_offering_id', 'Course offering', 'ref', True, reference='course-offerings'), Field('status', 'Status', 'choice', choices=(('ENROLLED', 'Enrolled'), ('DROPPED', 'Dropped'), ('COMPLETED', 'Completed')))),
        filters=(('student_id', 'Student', 'students'), ('course_offering_id', 'Offering', 'course-offerings'), ('status', 'Status', (('ENROLLED', 'Enrolled'), ('DROPPED', 'Dropped'), ('COMPLETED', 'Completed')))), sorts=(('enrollment_date', 'Enrollment date'),), delete=True),
    'grades': Resource('grades', 'Grades', (('enrollment_id', 'Enrollment'), ('midterm_grade', 'Midterm'), ('final_grade', 'Final'), ('remarks', 'Remarks'), ('status', 'Status')),
        (Field('enrollment_id', 'Enrollment', 'ref', True, reference='enrollments'), Field('midterm_grade', 'Midterm grade', 'decimal'), Field('final_grade', 'Final grade', 'decimal'), Field('remarks', 'Remarks'), Field('status', 'Status', 'choice', choices=(('DRAFT', 'Draft'), ('FINALIZED', 'Finalized')))),
        filters=(('enrollment_id', 'Enrollment', 'enrollments'), ('status', 'Status', (('DRAFT', 'Draft'), ('FINALIZED', 'Finalized'))),), sorts=(('final_grade', 'Final grade'), ('midterm_grade', 'Midterm grade')),
        write_roles=('ADMIN', 'REGISTRAR', 'INSTRUCTOR'), delete=False),
}


def display_for(resource, row):
    if resource.startswith('programs'):
        return f"{row.get('code')} - {row.get('name')}"
    if resource.startswith('courses'):
        return f"{row.get('course_code')} - {row.get('course_title')}"
    if resource.startswith('academic-terms'):
        return f"{row.get('academic_year')} {row.get('semester')}"
    if resource.startswith('users'):
        return f"{row.get('name')} ({row.get('email')})"
    if resource.startswith('students'):
        return f"{row.get('student_number')} - {row.get('last_name')}, {row.get('first_name')}"
    if resource.startswith('course-offerings'):
        return f"Offering #{row.get('id')} · section {row.get('section')}"
    if resource.startswith('enrollments'):
        return f"Enrollment #{row.get('id')} · student {row.get('student_id')}"
    return f"#{row.get('id')}"
