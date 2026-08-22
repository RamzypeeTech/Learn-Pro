from django.conf import settings
from django.db import models


class OwnedRecord(models.Model):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class UserProfile(models.Model):
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'
    PARENT = 'parent'
    ROLE_CHOICES = [(ADMIN, 'Administrator'), (TEACHER, 'Teacher'), (STUDENT, 'Student'), (PARENT, 'Parent / Guardian')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='school_profile')
    role = models.CharField(max_length=12, choices=ROLE_CHOICES, default=ADMIN)
    profile_photo = models.FileField(upload_to='profiles/users/', blank=True)
    teacher = models.OneToOneField('Teacher', null=True, blank=True, on_delete=models.SET_NULL, related_name='portal_profile')
    student = models.OneToOneField('Student', null=True, blank=True, on_delete=models.SET_NULL, related_name='portal_profile')
    parent = models.OneToOneField('ParentProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='portal_profile')

    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'


class SchoolClass(OwnedRecord):
    name = models.CharField(max_length=80)
    section = models.CharField(max_length=30, blank=True)
    academic_year = models.CharField(max_length=20, default='2026-27')

    class Meta:
        ordering = ['name', 'section']
        constraints = [models.UniqueConstraint(fields=['created_by', 'name', 'section', 'academic_year'], name='unique_school_class')]

    def __str__(self):
        return f'{self.name}{" - " + self.section if self.section else ""}'


class Teacher(OwnedRecord):
    full_name = models.CharField(max_length=120)
    employee_id = models.CharField(max_length=40)
    department = models.CharField(max_length=80, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    profile_photo = models.FileField(upload_to='profiles/teachers/', blank=True)

    class Meta:
        ordering = ['full_name']
        constraints = [models.UniqueConstraint(fields=['created_by', 'employee_id'], name='unique_teacher_employee_id')]

    def __str__(self):
        return self.full_name


class Student(OwnedRecord):
    full_name = models.CharField(max_length=120)
    student_id = models.CharField(max_length=40)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.PROTECT, related_name='students')
    enrollment_date = models.DateField()
    date_of_birth = models.DateField(null=True, blank=True)
    guardian_name = models.CharField(max_length=120, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    profile_photo = models.FileField(upload_to='profiles/students/', blank=True)

    class Meta:
        ordering = ['full_name']
        constraints = [models.UniqueConstraint(fields=['created_by', 'student_id'], name='unique_student_id')]

    def __str__(self):
        return self.full_name


class AttendanceRecord(OwnedRecord):
    PRESENT = 'present'
    LATE = 'late'
    ABSENT = 'absent'
    STATUS_CHOICES = [(PRESENT, 'Present'), (LATE, 'Late'), (ABSENT, 'Absent')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    attendance_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        ordering = ['-attendance_date', 'student__full_name']
        constraints = [models.UniqueConstraint(fields=['student', 'attendance_date'], name='one_attendance_per_student_day')]


class FeeRecord(OwnedRecord):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_records')
    invoice_number = models.CharField(max_length=40)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField()

    class Meta:
        ordering = ['due_date']
        constraints = [models.UniqueConstraint(fields=['created_by', 'invoice_number'], name='unique_fee_invoice')]

    @property
    def balance(self):
        return max(self.amount_due - self.amount_paid, 0)


class SchoolEvent(OwnedRecord):
    title = models.CharField(max_length=150)
    event_type = models.CharField(max_length=50, default='School event')
    scheduled_for = models.DateTimeField()
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.SET_NULL, related_name='events')

    class Meta:
        ordering = ['scheduled_for']


class GradeRecord(OwnedRecord):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grade_records')
    subject = models.CharField(max_length=100)
    assessment_name = models.CharField(max_length=120)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Optional individual assessment score (0 to 100).')
    first_term_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    second_term_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    third_term_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, editable=False)
    teacher_remark = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['student__full_name', 'subject']

    def save(self, *args, **kwargs):
        term_scores = [score for score in (self.first_term_score, self.second_term_score, self.third_term_score) if score is not None]
        self.final_score = sum(term_scores) / len(term_scores) if term_scores else self.score
        super().save(*args, **kwargs)


class AcademicYear(OwnedRecord):
    name = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    terms = models.PositiveSmallIntegerField(default=3)
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']
        constraints = [models.UniqueConstraint(fields=['created_by', 'name'], name='unique_academic_year_name')]


class Subject(OwnedRecord):
    CORE = 'core'
    ELECTIVE = 'elective'
    TYPE_CHOICES = [(CORE, 'Core'), (ELECTIVE, 'Elective')]
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.SET_NULL, related_name='subjects')
    teacher = models.ForeignKey(Teacher, null=True, blank=True, on_delete=models.SET_NULL, related_name='subjects')
    subject_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default=CORE)

    class Meta:
        ordering = ['name']
        constraints = [models.UniqueConstraint(fields=['created_by', 'code'], name='unique_subject_code')]


class Assignment(OwnedRecord):
    OPEN = 'open'
    CLOSED = 'closed'
    STATUS_CHOICES = [(OPEN, 'Open'), (CLOSED, 'Closed')]
    title = models.CharField(max_length=150)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    school_class = models.ForeignKey(SchoolClass, null=True, blank=True, on_delete=models.SET_NULL, related_name='assignments')
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OPEN)
    instructions = models.TextField(blank=True)

    class Meta:
        ordering = ['due_date']


class FinancialTransaction(OwnedRecord):
    INCOME = 'income'
    EXPENSE = 'expense'
    TYPE_CHOICES = [(INCOME, 'Income'), (EXPENSE, 'Expense')]
    name = models.CharField(max_length=150)
    transaction_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']


class ModuleRecord(OwnedRecord):
    """Reusable operational record for the school service workspaces."""
    module = models.CharField(max_length=30)
    title = models.CharField(max_length=160)
    reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=40, blank=True)
    record_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-record_date', '-created_at']


class Announcement(OwnedRecord):
    """A text-first noticeboard post, deliberately kept free of images."""
    title = models.CharField(max_length=180)
    body = models.TextField()
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-created_at']


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='school_notifications')
    title = models.CharField(max_length=180)
    message = models.TextField()
    url = models.CharField(max_length=250, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class LoginActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='login_activities')
    signed_in_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-signed_in_at']


class ParentProfile(OwnedRecord):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'
    GENDER_CHOICES = [(MALE, 'Male'), (FEMALE, 'Female'), (OTHER, 'Other')]
    first_name = models.CharField(max_length=70)
    last_name = models.CharField(max_length=70)
    parent_id = models.CharField(max_length=40)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    occupation = models.CharField(max_length=100, blank=True)
    blood_group = models.CharField(max_length=4, blank=True)
    religion = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    ward = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL, related_name='parents')

    class Meta:
        ordering = ['first_name', 'last_name']
        constraints = [models.UniqueConstraint(fields=['created_by', 'parent_id'], name='unique_parent_id')]

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class LibraryBook(OwnedRecord):
    title = models.CharField(max_length=180)
    author = models.CharField(max_length=120)
    isbn = models.CharField(max_length=30, blank=True)
    category = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True)
    cover_image = models.FileField(upload_to='library/covers/', blank=True)
    reading_file = models.FileField(upload_to='library/books/')

    class Meta:
        ordering = ['title']
        constraints = [models.UniqueConstraint(fields=['created_by', 'title', 'author'], name='unique_library_book')]

    def __str__(self):
        return self.title

    @property
    def is_pdf(self):
        return self.reading_file.name.lower().endswith('.pdf')
