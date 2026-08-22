from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.db.models import Avg, Q
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from .forms import AcademicYearForm, AnnouncementForm, AssignmentForm, AttendanceForm, EventForm, FeeForm, FinancialTransactionForm, GradeRecordForm, LibraryBookForm, ModuleRecordForm, ParentProfileForm, SchoolClassForm, StudentForm, StudentPhotoForm, SubjectForm, TeacherForm, TeacherPhotoForm, UserProfileForm
from .models import AcademicYear, Announcement, Assignment, AttendanceRecord, FeeRecord, FinancialTransaction, GradeRecord, LibraryBook, LoginActivity, ModuleRecord, Notification, ParentProfile, SchoolClass, SchoolEvent, Student, Subject, Teacher, UserProfile


class SchoolLoginForm(AuthenticationForm):
    """Login form that requires acknowledgement of the school terms."""

    def clean(self):
        cleaned_data = super().clean()
        if not self.data.get('accept_terms'):
            self.add_error(None, 'You must agree to the Terms and Conditions to continue.')
        return cleaned_data


class CreateAccountForm(UserCreationForm):
    """New school workspace account with an explicit terms acknowledgement."""

    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label='Account type')
    profile_photo = forms.FileField(required=False, label='Profile photo')
    accept_terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms and Conditions to create an account.'},
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if not photo:
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Choose an image smaller than 5 MB.')
        if getattr(photo, 'content_type', '').split('/')[0] != 'image':
            raise forms.ValidationError('Upload a JPG, PNG, or WebP image.')
        return photo




@login_required
def index(request):
    """Renders the main dashboard/index page."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.role != UserProfile.ADMIN:
        return role_dashboard(request, profile)
    today = timezone.localdate()
    students = Student.objects.all()
    attendance_today = AttendanceRecord.objects.filter(attendance_date=today)
    # Financial figures on the main dashboard belong only to the signed-in
    # workspace owner; they must never combine another user's fee records.
    fee_records = FeeRecord.objects.filter(created_by=request.user)
    total_due = sum((record.amount_due for record in fee_records), start=0)
    total_collected = sum((record.amount_paid for record in fee_records), start=0)
    pending_balance = sum((record.balance for record in fee_records), start=0)
    attendance_total = attendance_today.count()
    attended_count = attendance_today.filter(status__in=[AttendanceRecord.PRESENT, AttendanceRecord.LATE]).count()
    attendance_days = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        records = AttendanceRecord.objects.filter(attendance_date=day)
        total = records.count()
        present = records.filter(status__in=[AttendanceRecord.PRESENT, AttendanceRecord.LATE]).count()
        attendance_days.append({'label': day.strftime('%a'), 'percentage': round(present / total * 100) if total else 0, 'has_records': bool(total)})
    grade_bands = [('A+ / A', 70), ('B', 60), ('C', 50), ('D', 40), ('F', 0)]
    student_averages = GradeRecord.objects.all().values('student').annotate(average=Avg('final_score'))
    graded_students = student_averages.count()
    grade_distribution = []
    for index, (label, minimum) in enumerate(grade_bands):
        maximum = grade_bands[index - 1][1] - 0.01 if index else 100
        count = sum(1 for average in student_averages if minimum <= average['average'] <= maximum)
        grade_distribution.append({'label': label, 'count': count, 'percentage': round(count / graded_students * 100) if graded_students else 0})
    context = {
        'total_students': students.filter(enrollment_date__year=today.year).count(),
        'total_teachers': Teacher.objects.count(),
        'total_classes': SchoolClass.objects.count(),
        'attendance_percentage': round((attended_count / attendance_total) * 100) if attendance_total else None,
        'attendance_total': attendance_total,
        'pending_balance': pending_balance,
        'pending_fee_count': sum(1 for record in fee_records if record.balance > 0),
        'fee_collected': total_collected,
        'fee_collection_percentage': round(total_collected / total_due * 100) if total_due else 0,
        'attendance_days': attendance_days,
        'grade_distribution': grade_distribution,
        'graded_students': graded_students,
        'upcoming_events': SchoolEvent.objects.filter(scheduled_for__gte=timezone.now()).count(),
        'next_event': SchoolEvent.objects.filter(scheduled_for__gte=timezone.now()).first(),
    }
    return render(request, 'index.html', context)


def role_dashboard(request, profile):
    """Role-specific portal home pages, limited to the account's linked record."""
    context = {'profile': profile, 'active': 'dashboard'}
    if profile.role == UserProfile.ADMIN:
        context.update({'person': request.user, 'total_students': Student.objects.count(), 'total_teachers': Teacher.objects.count(), 'total_classes': SchoolClass.objects.count()})
    elif profile.role == UserProfile.STUDENT and profile.student:
        student = Student.objects.select_related('school_class').get(pk=profile.student_id)
        attendance = student.attendance_records.all()
        total = attendance.count()
        present = attendance.filter(status__in=[AttendanceRecord.PRESENT, AttendanceRecord.LATE]).count()
        fees = student.fee_records.all()
        context.update({'person': student, 'school_class': student.school_class, 'subjects': Subject.objects.filter(school_class=student.school_class), 'attendance_percentage': round(present / total * 100) if total else None, 'grade_average': student.grade_records.aggregate(average=Avg('final_score'))['average'], 'student_pending_fee': sum((fee.balance for fee in fees), start=0)})
    elif profile.role == UserProfile.TEACHER and profile.teacher:
        teacher = Teacher.objects.get(pk=profile.teacher_id)
        context.update({'person': teacher, 'subjects': teacher.subjects.select_related('school_class'), 'student_count': Student.objects.filter(created_by=teacher.created_by, school_class__subjects__teacher=teacher).distinct().count()})
    elif profile.role == UserProfile.PARENT and profile.parent:
        parent = ParentProfile.objects.select_related('ward', 'ward__school_class').get(pk=profile.parent_id)
        context.update({'person': parent, 'ward': parent.ward})
    if 'person' not in context:
        context.update({
            'portal_setup': True,
            'total_students': Student.objects.count(),
            'total_teachers': Teacher.objects.count(),
            'total_classes': SchoolClass.objects.count(),
        })
    return render(request, 'role_dashboard.html', context)


def workspace_owner(profile):
    """Return the administrator workspace that owns a linked portal record."""
    for record in (profile.teacher, profile.student, profile.parent):
        if record:
            return record.created_by
    return profile.user


def module_scope(request, kind):
    """Return the current workspace with every signed-in role able to use it."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    owner = workspace_owner(profile)
    return profile, owner, True, {}


ROLE_MODULE_ACCESS = {
    UserProfile.TEACHER: set(),
    UserProfile.STUDENT: set(),
    UserProfile.PARENT: set(),
}


def can_view_student(request, student):
    return True


def can_access_module(request, key):
    return True

# School management pages. These currently use sample data so the interface is
# usable before the database models are connected.
def management_page(request, page, title, section, intro, action, **extra):
    context = {'page': page, 'active': page, 'title': title, 'section': section,
               'intro': intro, 'action': action, **extra}
    return render(request, 'management-page.html', context)


MODULE_PAGES = {
    'announcements': ('Announcements & Noticeboard', 'Communication', 'Publish important updates for staff, students, and parents.', 'fa-bullhorn', ['School-wide announcements', 'Holiday and event reminders', 'Urgent notice publishing']),
    'parents': ('Parent Portal & Directory', 'Communication', 'Give parents a secure view of their child’s progress, attendance, and fee balance.', 'fa-people-roof', ['Parent and guardian directory', 'Ward performance overview', 'Fee balance and communication history']),
    'messages': ('Messages & Internal Chat', 'Communication', 'Keep conversations between administrators, staff, and parents organised and traceable.', 'fa-comments', ['Direct messages', 'Support tickets and follow-ups', 'Conversation history']),
    'timetable': ('Timetable & Scheduling', 'Operations', 'Plan class periods, room allocations, teacher schedules, and examination timetables.', 'fa-calendar-days', ['Daily period schedules', 'Room and teacher assignments', 'Exam timetable planning']),
    'transport': ('Transport & Route Management', 'Operations', 'Manage vehicles, drivers, routes, and student pickup or drop-off records.', 'fa-bus', ['Vehicle and driver register', 'Route assignments', 'Pickup and drop-off logs']),
    'library': ('Library Management', 'Operations', 'Catalogue books, record issue and return activity, and monitor overdue items.', 'fa-book', ['Book catalogue', 'Issue and return tracking', 'Overdue fine records']),
    'hr_payroll': ('Staff HR & Payroll', 'Human Resources', 'Manage employee records, leave, salary structures, deductions, and payslips.', 'fa-money-check-dollar', ['Leave requests', 'Salary and deduction records', 'Monthly payroll preparation']),
    'system_settings': ('System Settings & Audit Logs', 'Administration', 'Control workspace settings, access permissions, academic sessions, and security activity.', 'fa-shield-halved', ['Role and permission settings', 'Academic session controls', 'Security audit history']),
    'reports': ('Reports & Analytics', 'Administration', 'Prepare school records, financial summaries, registers, and performance reports.', 'fa-chart-line', ['Academic report cards', 'Finance and payroll summaries', 'Master registers and exports']),
}


def module_page(request, key):
    if not can_access_module(request, key):
        title = MODULE_PAGES[key][0]
        return render(request, 'access_denied.html', {'active': key, 'title': title})
    title, section, intro, icon, features = MODULE_PAGES[key]
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    can_create = True
    form = ModuleRecordForm(request.POST or None) if can_create else None
    if request.method == 'POST' and can_create and form.is_valid():
        record = form.save(commit=False)
        record.module = key
        record.created_by = workspace_owner(profile)
        record.save()
        messages.success(request, f'{title} record saved successfully.')
        return redirect(key)
    owner = workspace_owner(profile)
    return render(request, 'module_page.html', {'title': title, 'section': section, 'intro': intro, 'icon': icon, 'features': features, 'active': key, 'form': form, 'can_create': can_create, 'records': ModuleRecord.objects.filter(module=key)})


def record_page(request, kind):
    """Create and list operational records belonging to the signed-in school."""
    configurations = {
        'years': ('Academic Years', 'Add school sessions and select the current active year.', 'Add academic year', AcademicYear, AcademicYearForm),
        'classes': ('Classes', 'Create a class and keep your class list organised.', 'Add class', SchoolClass, SchoolClassForm),
        'teachers': ('Teachers', 'Maintain an up-to-date staff and teacher register.', 'Add teacher', Teacher, TeacherForm),
        'students': ('Students', 'Record every student enrolled in this academic year.', 'Add student', Student, StudentForm),
        'attendance': ('Attendance', 'Record each student’s daily attendance status.', 'Record attendance', AttendanceRecord, AttendanceForm),
        'fees': ('Fees', 'Record invoices and track outstanding fee balances.', 'Add fee record', FeeRecord, FeeForm),
        'events': ('Events & Exams', 'Schedule examinations and school events in one calendar.', 'Schedule event', SchoolEvent, EventForm),
        'grades': ('Results', 'Record student assessment scores for the grade distribution.', 'Record result', GradeRecord, GradeRecordForm),
        'subjects': ('Subjects', 'Create subjects and assign them to a class and teacher.', 'Add subject', Subject, SubjectForm),
        'assignments': ('Assignments', 'Create coursework and track its due date and status.', 'Add assignment', Assignment, AssignmentForm),
        'finance': ('Financial Management', 'Add income and expenses to keep cash flow current.', 'Add transaction', FinancialTransaction, FinancialTransactionForm),
    }
    title, intro, action, model, form_class = configurations[kind]
    profile, owner, can_create, filters = module_scope(request, kind)
    if filters is None:
        return render(request, 'access_denied.html', {'active': kind, 'title': title})
    editing_record = None
    if can_create and request.GET.get('edit'):
        editing_record = get_object_or_404(model, pk=request.GET['edit'])
    form = form_class(request.POST or None, request.FILES or None, instance=editing_record) if can_create else None
    # Prevent one user from assigning another user's classes or students.
    allowed_classes = SchoolClass.objects.all()
    if profile.role == UserProfile.TEACHER and profile.teacher:
        allowed_classes = allowed_classes.filter(subjects__teacher=profile.teacher).distinct()
    if form and 'school_class' in form.fields:
        form.fields['school_class'].queryset = allowed_classes
    if form and 'student' in form.fields:
        form.fields['student'].queryset = Student.objects.filter(school_class__in=allowed_classes)
    if form and 'teacher' in form.fields:
        form.fields['teacher'].queryset = Teacher.objects.all()
    if form and 'subject' in form.fields:
        subjects = Subject.objects.all()
        if profile.role == UserProfile.TEACHER and profile.teacher:
            subjects = subjects.filter(teacher=profile.teacher)
        form.fields['subject'].queryset = subjects
    if request.method == 'POST' and form and form.is_valid():
        record = form.save(commit=False)
        if not record.created_by_id:
            record.created_by = owner
        if kind == 'years' and record.is_active:
            AcademicYear.objects.filter(created_by=request.user, is_active=True).update(is_active=False)
        record.save()
        messages.success(request, f'{title[:-1] if title.endswith("s") else title} updated successfully.' if editing_record else f'{title[:-1] if title.endswith("s") else title} saved successfully.')
        return redirect({'years': 'academic_years', 'classes': 'classes', 'teachers': 'teachers', 'students': 'students', 'attendance': 'attendance', 'fees': 'fees', 'events': 'exams_results', 'grades': 'results', 'subjects': 'subjects', 'assignments': 'assignments', 'finance': 'financial_management'}[kind])
    if request.method == 'POST' and request.POST.get('delete'):
        record = get_object_or_404(model, pk=request.POST['delete'])
        record.delete()
        messages.success(request, 'Record deleted successfully.')
        return redirect({'years': 'academic_years', 'classes': 'classes', 'teachers': 'teachers', 'students': 'students', 'attendance': 'attendance', 'fees': 'fees', 'events': 'exams_results', 'grades': 'results', 'subjects': 'subjects', 'assignments': 'assignments', 'finance': 'financial_management'}[kind])
    records = model.objects.filter(**filters).distinct()
    if kind in ('students', 'events', 'subjects', 'assignments'):
        records = records.select_related('school_class')
    elif kind in ('attendance', 'fees', 'grades'):
        records = records.select_related('student', 'student__school_class')
    if kind == 'subjects':
        records = records.select_related('school_class', 'teacher')
    if kind == 'assignments':
        records = records.select_related('subject', 'school_class')
    if kind == 'finance':
        income = sum((item.amount for item in records if item.transaction_type == FinancialTransaction.INCOME), start=0)
        expenses = sum((item.amount for item in records if item.transaction_type == FinancialTransaction.EXPENSE), start=0)
    else:
        income = expenses = 0
    return render(request, 'records.html', {
        'kind': kind, 'title': title, 'intro': intro, 'action': action, 'form': form,
        'records': records, 'income': income, 'expenses': expenses, 'net_balance': income - expenses, 'active': kind, 'can_create': can_create, 'can_edit': can_create, 'editing_record': editing_record,
    })


@login_required
def academic_years(request):
    return record_page(request, 'years')


@login_required
def classes(request):
    return record_page(request, 'classes')


@login_required
def teachers(request):
    return record_page(request, 'teachers')


@login_required
def students(request):
    return record_page(request, 'students')


@login_required
def student_details(request, student_id):
    student = get_object_or_404(Student.objects.select_related('school_class'), pk=student_id)
    if not can_view_student(request, student):
        return render(request, 'access_denied.html', {'active': 'students', 'title': 'Student details'})
    attendance = student.attendance_records.all()
    attendance_total = attendance.count()
    attendance_good = attendance.filter(status__in=[AttendanceRecord.PRESENT, AttendanceRecord.LATE]).count()
    grade_average = student.grade_records.aggregate(average=Avg('score'))['average']
    fee_balance = sum((fee.balance for fee in student.fee_records.all()), start=0)
    return render(request, 'person_details.html', {
        'person': student, 'person_type': 'Student', 'back_url': 'students', 'active': 'students',
        'attendance_percentage': round(attendance_good / attendance_total * 100) if attendance_total else None,
        'grade_average': grade_average, 'fee_balance': fee_balance,
        'photo_form': StudentPhotoForm(instance=student) if UserProfile.objects.get(user=request.user).role == UserProfile.ADMIN else None,
        'photo_update_url': reverse('update_student_photo', args=[student.pk]),
    })


@login_required
def teacher_details(request, teacher_id):
    teacher = get_object_or_404(Teacher.objects.prefetch_related('subjects__school_class'), pk=teacher_id)
    return render(request, 'person_details.html', {
        'person': teacher, 'person_type': 'Teacher', 'back_url': 'teachers', 'active': 'teachers',
        'subjects': teacher.subjects.all(),
        'photo_form': TeacherPhotoForm(instance=teacher), 'photo_update_url': reverse('update_teacher_photo', args=[teacher.pk]),
    })


@login_required
def update_student_photo(request, student_id):
    student = get_object_or_404(Student, pk=student_id)
    if request.method == 'POST':
        form = StudentPhotoForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student profile photo updated.')
        else:
            messages.error(request, 'Please upload a JPG, PNG, or WebP image smaller than 5 MB.')
    return redirect('student_details', student_id=student.pk)


@login_required
def update_teacher_photo(request, teacher_id):
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    if request.method == 'POST':
        form = TeacherPhotoForm(request.POST, request.FILES, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Teacher profile photo updated.')
        else:
            messages.error(request, 'Please upload a JPG, PNG, or WebP image smaller than 5 MB.')
    return redirect('teacher_details', teacher_id=teacher.pk)


@login_required
def subjects(request):
    return record_page(request, 'subjects')


@login_required
def attendance(request):
    return record_page(request, 'attendance')


@login_required
def exams_results(request):
    return record_page(request, 'events')


@login_required
def results(request):
    return record_page(request, 'grades')


@login_required
def assignments(request):
    return record_page(request, 'assignments')


@login_required
def fees(request):
    return record_page(request, 'fees')


@login_required
def financial_management(request):
    return record_page(request, 'finance')


@login_required
def search(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        students = Student.objects.all()
        subjects = Subject.objects.all()
        assignments = Assignment.objects.all()
        classes = SchoolClass.objects.all()
        for record in students.filter(Q(full_name__icontains=query) | Q(student_id__icontains=query))[:20]:
            results.append({'type': 'Student', 'name': record.full_name, 'detail': f'{record.student_id} · {record.school_class}', 'url': reverse('student_details', args=[record.pk])})
        for record in Teacher.objects.filter(Q(full_name__icontains=query) | Q(employee_id__icontains=query))[:20]:
            results.append({'type': 'Teacher', 'name': record.full_name, 'detail': record.employee_id, 'url': reverse('teacher_details', args=[record.pk])})
        for record in classes.filter(name__icontains=query)[:20]:
            results.append({'type': 'Class', 'name': str(record), 'detail': record.academic_year, 'url': reverse('classes')})
        for record in subjects.filter(Q(name__icontains=query) | Q(code__icontains=query))[:20]:
            results.append({'type': 'Subject', 'name': record.name, 'detail': record.code, 'url': reverse('subjects')})
        for record in assignments.filter(title__icontains=query)[:20]:
            results.append({'type': 'Assignment', 'name': record.title, 'detail': str(record.subject), 'url': reverse('assignments')})
        for record in FinancialTransaction.objects.filter(name__icontains=query)[:20]:
            results.append({'type': 'Transaction', 'name': record.name, 'detail': f'₦{record.amount}', 'url': reverse('financial_management')})
    return render(request, 'search_results.html', {'query': query, 'results': results})


@login_required
def announcements(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    owner = workspace_owner(profile)
    form = AnnouncementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.created_by = owner
        post.save()
        messages.success(request, 'Announcement published and school notifications sent.')
        return redirect('announcements')
    return render(request, 'announcements.html', {'form': form, 'announcements': Announcement.objects.all(), 'active': 'announcements'})


@login_required
def parents(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    owner = workspace_owner(profile)
    can_edit = True
    form = ParentProfileForm(request.POST or None) if can_edit else None
    if form:
        form.fields['ward'].queryset = Student.objects.all()
    if request.method == 'POST' and form and form.is_valid():
        parent = form.save(commit=False)
        parent.created_by = owner
        parent.save()
        messages.success(request, 'Parent profile created successfully.')
        return redirect('parents')
    query = request.GET.get('q', '').strip()
    parent_list = ParentProfile.objects.all().select_related('ward')
    if query:
        parent_list = parent_list.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(parent_id__icontains=query) | Q(phone__icontains=query))
    return render(request, 'parents.html', {'form': form, 'parents': parent_list, 'query': query, 'active': 'parents', 'can_edit': can_edit})


@login_required
def parent_details(request, parent_id):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    parent = get_object_or_404(ParentProfile.objects.select_related('ward'), pk=parent_id)
    ward = parent.ward
    fees = FeeRecord.objects.filter(student=ward) if ward else []
    fee_balance = sum((fee.balance for fee in fees), start=0)
    attendance = AttendanceRecord.objects.filter(student=ward) if ward else []
    attendance_total = attendance.count() if ward else 0
    attendance_good = attendance.filter(status__in=[AttendanceRecord.PRESENT, AttendanceRecord.LATE]).count() if ward else 0
    grade_average = GradeRecord.objects.filter(student=ward).aggregate(average=Avg('final_score'))['average'] if ward else None
    return render(request, 'parent_details.html', {'parent': parent, 'ward': ward, 'fee_balance': fee_balance, 'attendance_percentage': round(attendance_good / attendance_total * 100) if attendance_total else None, 'grade_average': grade_average, 'active': 'parents'})


@login_required
def messages_page(request):
    return module_page(request, 'messages')


@login_required
def timetable(request):
    return module_page(request, 'timetable')


@login_required
def transport(request):
    return module_page(request, 'transport')


@login_required
def library(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    owner = workspace_owner(profile)
    can_add_books = True
    form = LibraryBookForm(request.POST or None, request.FILES or None) if can_add_books else None
    if request.method == 'POST' and not can_add_books:
        messages.error(request, 'Only administrators can add books to the school library.')
        return redirect('library')
    if request.method == 'POST' and form.is_valid():
        book = form.save(commit=False)
        book.created_by = owner
        book.save()
        messages.success(request, 'Book added to the library.')
        return redirect('library')
    return render(request, 'library.html', {'form': form, 'books': LibraryBook.objects.all(), 'active': 'library', 'can_add_books': can_add_books})


@login_required
def read_book(request, book_id):
    book = get_object_or_404(LibraryBook, pk=book_id)
    return render(request, 'book_reader.html', {'book': book, 'active': 'library'})


@login_required
def hr_payroll(request):
    return module_page(request, 'hr_payroll')


@login_required
def system_settings(request):
    return module_page(request, 'system_settings')


@login_required
def reports(request):
    return module_page(request, 'reports')


def sign_in(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = SchoolLoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        logged_in_user = form.get_user()
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        LoginActivity.objects.create(user=logged_in_user, ip_address=(forwarded_for.split(',')[0].strip() or request.META.get('REMOTE_ADDR')))
        recipients = [email for email in (logged_in_user.email, settings.ADMIN_LOGIN_NOTIFICATION_EMAIL) if email]
        if recipients:
            send_mail(
                'Learn Pro login notification',
                f'{logged_in_user.get_full_name() or logged_in_user.username} signed in to Learn Pro on {timezone.localtime():%d %B %Y at %H:%M}.',
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=True,
            )
        # By default the session ends when the browser closes. "Remember me"
        # opts into Django's normal two-week persistent session.
        if request.POST.get('remember_me'):
            request.session.set_expiry(1209600)
        else:
            request.session.set_expiry(0)
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url and url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(next_url)
        return redirect('index')
    return render(request, 'registration/login.html', {'form': form})


@login_required
def set_academic_year(request):
    if request.method == 'POST':
        request.session['selected_academic_year'] = request.POST.get('academic_year', '')
    return redirect(request.POST.get('next') or 'index')


def create_account(request):
    if request.user.is_authenticated:
        return redirect('index')

    form = CreateAccountForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = form.cleaned_data['role']
        profile.profile_photo = form.cleaned_data.get('profile_photo') or profile.profile_photo
        profile.save()
        login(request, user)
        messages.success(request, 'Your account has been created. Welcome to Learn Pro!')
        return redirect('index')
    return render(request, 'registration/create_account.html', {'form': form})


@login_required
def notifications(request):
    items = Notification.objects.filter(user=request.user)
    items.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {'notifications': items, 'active': 'notifications'})


@login_required
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Your password has been changed.')
        return redirect('index')
    return render(request, 'registration/change_password.html', {'form': form})


@login_required
def my_profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    form = UserProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Your profile photo has been updated.')
        return redirect('my_profile')
    return render(request, 'my_profile.html', {'form': form, 'profile': profile})


@login_required
def sign_out(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been signed out.')
    return redirect('sign_in')
