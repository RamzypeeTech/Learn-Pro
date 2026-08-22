from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from .models import AttendanceRecord, FeeRecord, GradeRecord, ParentProfile, SchoolClass, SchoolEvent, Student, Subject, Teacher, UserProfile
from .forms import StudentPhotoForm


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='schooladmin', password='OldPassword123!'
        )

    def test_dashboard_requires_sign_in(self):
        response = self.client.get(reverse('index'))
        self.assertRedirects(response, f"{reverse('sign_in')}?next={reverse('index')}")

    def test_sign_in_requires_terms_acceptance(self):
        response = self.client.post(reverse('sign_in'), {
            'username': 'schooladmin', 'password': 'OldPassword123!',
        })
        self.assertContains(response, 'Terms and Conditions')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_remember_me_creates_persistent_session(self):
        response = self.client.post(reverse('sign_in'), {
            'username': 'schooladmin', 'password': 'OldPassword123!',
            'accept_terms': 'on', 'remember_me': 'on',
        })
        self.assertRedirects(response, reverse('index'))
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_new_user_can_create_an_account_after_accepting_terms(self):
        response = self.client.post(reverse('create_account'), {
            'first_name': 'Ada',
            'last_name': 'Okafor',
            'username': 'adaokafor',
            'email': 'ada@example.com',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'role': UserProfile.ADMIN,
            'accept_terms': 'on',
        })
        self.assertRedirects(response, reverse('index'))
        new_user = get_user_model().objects.get(username='adaokafor')
        self.assertEqual(new_user.email, 'ada@example.com')
        self.assertEqual(str(new_user.pk), self.client.session.get('_auth_user_id'))
        self.assertEqual(new_user.school_profile.role, UserProfile.ADMIN)

    def test_password_change_keeps_user_signed_in(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('change_password'), {
            'old_password': 'OldPassword123!',
            'new_password1': 'NewPassword123!',
            'new_password2': 'NewPassword123!',
        })
        self.assertRedirects(response, reverse('index'))
        self.assertEqual(str(self.user.pk), self.client.session.get('_auth_user_id'))

    def test_dashboard_uses_the_signed_in_users_records(self):
        school_class = SchoolClass.objects.create(created_by=self.user, name='Grade 10', section='A')
        student = Student.objects.create(created_by=self.user, full_name='Ada Okafor', student_id='STD-1', school_class=school_class, enrollment_date=timezone.localdate())
        Teacher.objects.create(created_by=self.user, full_name='Amina Khan', employee_id='TCH-1')
        AttendanceRecord.objects.create(created_by=self.user, student=student, attendance_date=timezone.localdate(), status=AttendanceRecord.PRESENT)
        FeeRecord.objects.create(created_by=self.user, student=student, invoice_number='INV-1', amount_due=10000, amount_paid=4000, due_date=timezone.localdate())
        SchoolEvent.objects.create(created_by=self.user, title='First term exam', scheduled_for=timezone.now() + timedelta(days=2))
        self.client.force_login(self.user)

        response = self.client.get(reverse('index'))

        self.assertContains(response, '>1</div>')
        self.assertContains(response, '₦6000')
        self.assertContains(response, 'First term exam')

    def test_student_profile_is_viewable_and_accepts_an_image_upload(self):
        school_class = SchoolClass.objects.create(created_by=self.user, name='SS1', section='A')
        student = Student.objects.create(created_by=self.user, full_name='Ada Okafor', student_id='STD-1', school_class=school_class, enrollment_date=timezone.localdate())
        self.client.force_login(self.user)

        response = self.client.get(reverse('student_details', args=[student.pk]))
        self.assertContains(response, 'Student details')
        self.assertContains(response, 'SS1 - A')

        from django.core.files.uploadedfile import SimpleUploadedFile
        photo = SimpleUploadedFile('ada.jpg', b'image-data', content_type='image/jpeg')
        self.assertTrue(StudentPhotoForm(files={'profile_photo': photo}, instance=student).is_valid())

    def test_teacher_profile_is_viewable(self):
        teacher = Teacher.objects.create(created_by=self.user, full_name='Amina Khan', employee_id='TCH-1', department='Sciences')
        self.client.force_login(self.user)

        response = self.client.get(reverse('teacher_details', args=[teacher.pk]))
        self.assertContains(response, 'Teacher details')
        self.assertContains(response, 'Sciences')

    def test_linked_student_receives_student_dashboard(self):
        school_class = SchoolClass.objects.create(created_by=self.user, name='SS1', section='A')
        student = Student.objects.create(created_by=self.user, full_name='Ada Okafor', student_id='STD-1', school_class=school_class, enrollment_date=timezone.localdate())
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.role = UserProfile.STUDENT
        profile.student = student
        profile.save()
        self.client.force_login(self.user)

        response = self.client.get(reverse('index'))

        self.assertContains(response, 'Student portal')
        self.assertContains(response, 'SS1 - A')

    def test_term_scores_calculate_a_final_result_and_keep_teacher_remark(self):
        school_class = SchoolClass.objects.create(created_by=self.user, name='SS2', section='A')
        student = Student.objects.create(created_by=self.user, full_name='Chidi Okeke', student_id='STD-2', school_class=school_class, enrollment_date=timezone.localdate())
        result = GradeRecord.objects.create(
            created_by=self.user, student=student, subject='Mathematics', assessment_name='2026 Final Result',
            first_term_score=80, second_term_score=70, third_term_score=90, teacher_remark='Excellent work.',
        )
        self.assertEqual(result.final_score, 80)
        self.assertEqual(result.teacher_remark, 'Excellent work.')


class RoleAccessTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username='admin', password='SecurePassword123!')
        self.school_class = SchoolClass.objects.create(created_by=self.admin, name='SS1', section='A')
        self.student = Student.objects.create(created_by=self.admin, full_name='Ada Okafor', student_id='STD-1', school_class=self.school_class, enrollment_date=timezone.localdate())
        self.teacher = Teacher.objects.create(created_by=self.admin, full_name='Amina Khan', employee_id='TCH-1')
        self.subject = Subject.objects.create(created_by=self.admin, name='Mathematics', code='MTH-1', school_class=self.school_class, teacher=self.teacher)
        AttendanceRecord.objects.create(created_by=self.admin, student=self.student, attendance_date=timezone.localdate(), status=AttendanceRecord.PRESENT)
        GradeRecord.objects.create(created_by=self.admin, student=self.student, subject='Mathematics', assessment_name='Test 1', score=85)
        self.student_user = get_user_model().objects.create_user(username='student', password='SecurePassword123!')
        student_profile = self.student_user.school_profile
        student_profile.role = UserProfile.STUDENT
        student_profile.student = self.student
        student_profile.save()
        self.parent = ParentProfile.objects.create(created_by=self.admin, first_name='Grace', last_name='Okafor', parent_id='PAR-1', gender=ParentProfile.FEMALE, phone='08000000000', ward=self.student)
        self.parent_user = get_user_model().objects.create_user(username='parent', password='SecurePassword123!')
        parent_profile = self.parent_user.school_profile
        parent_profile.role = UserProfile.PARENT
        parent_profile.parent = self.parent
        parent_profile.save()
        self.teacher_user = get_user_model().objects.create_user(username='teacher', password='SecurePassword123!')
        teacher_profile = self.teacher_user.school_profile
        teacher_profile.role = UserProfile.TEACHER
        teacher_profile.teacher = self.teacher
        teacher_profile.save()

    def test_teacher_can_open_all_operational_pages(self):
        self.client.force_login(self.teacher_user)
        for url_name in ('classes', 'students', 'subjects', 'attendance', 'results', 'assignments', 'announcements', 'messages', 'timetable', 'reports'):
            self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)
        for url_name in ('academic_years', 'fees', 'financial_management', 'teachers', 'exams_results', 'parents', 'library'):
            self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)

    def test_student_and_parent_can_create_records_in_their_workspace(self):
        allowed = ('academic_years', 'classes', 'students', 'subjects', 'attendance', 'exams_results', 'results', 'assignments', 'fees', 'announcements', 'timetable', 'reports')
        for offset, user in enumerate((self.student_user, self.parent_user), start=1):
            self.client.force_login(user)
            for url_name in allowed:
                self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)
            response = self.client.post(reverse('attendance'), {'student': self.student.pk, 'attendance_date': timezone.localdate() + timedelta(days=offset), 'status': AttendanceRecord.ABSENT})
            self.assertRedirects(response, reverse('attendance'))
            self.assertEqual(AttendanceRecord.objects.filter(student=self.student).count(), offset + 1)
            self.assertTemplateUsed(self.client.get(reverse('financial_management')), 'records.html')
