from django import forms
from .models import AcademicYear, Announcement, Assignment, AttendanceRecord, FeeRecord, FinancialTransaction, GradeRecord, LibraryBook, ModuleRecord, ParentProfile, SchoolClass, SchoolEvent, Student, Subject, Teacher, UserProfile


class ProfilePhotoValidationMixin:
    """Keep profile uploads small and image-only without adding an image library."""

    def clean_profile_photo(self):
        photo = self.cleaned_data.get('profile_photo')
        if not photo:
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Choose an image smaller than 5 MB.')
        if getattr(photo, 'content_type', '').split('/')[0] != 'image':
            raise forms.ValidationError('Upload an image file (JPG, PNG, or WebP).')
        return photo


class SchoolClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ('name', 'section', 'academic_year')
        labels = {'name': 'Class level', 'section': 'Section'}
        help_texts = {'name': 'For example: SS1, JSS2, Primary 4.', 'section': 'For example: A, B, or Science.'}


class TeacherForm(ProfilePhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ('full_name', 'employee_id', 'department', 'job_title', 'email', 'phone', 'profile_photo')


class StudentForm(ProfilePhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = Student
        fields = ('full_name', 'student_id', 'school_class', 'enrollment_date', 'date_of_birth', 'guardian_name', 'guardian_phone', 'email', 'profile_photo')
        widgets = {'enrollment_date': forms.DateInput(attrs={'type': 'date'}), 'date_of_birth': forms.DateInput(attrs={'type': 'date'})}


class StudentPhotoForm(ProfilePhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = Student
        fields = ('profile_photo',)


class TeacherPhotoForm(ProfilePhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ('profile_photo',)


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ('student', 'attendance_date', 'status')
        widgets = {'attendance_date': forms.DateInput(attrs={'type': 'date'})}


class FeeForm(forms.ModelForm):
    class Meta:
        model = FeeRecord
        fields = ('student', 'invoice_number', 'amount_due', 'amount_paid', 'due_date')
        widgets = {'due_date': forms.DateInput(attrs={'type': 'date'})}


class EventForm(forms.ModelForm):
    class Meta:
        model = SchoolEvent
        fields = ('title', 'event_type', 'scheduled_for', 'school_class')
        widgets = {'scheduled_for': forms.DateTimeInput(attrs={'type': 'datetime-local'})}


class GradeRecordForm(forms.ModelForm):
    class Meta:
        model = GradeRecord
        fields = ('student', 'subject', 'assessment_name', 'score', 'first_term_score', 'second_term_score', 'third_term_score', 'teacher_remark')
        widgets = {
            'score': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
            'first_term_score': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
            'second_term_score': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
            'third_term_score': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': '0.01'}),
            'teacher_remark': forms.TextInput(attrs={'placeholder': 'e.g. Excellent progress. Keep it up.'}),
        }

    def clean_score(self):
        score = self.cleaned_data['score']
        if score is not None and not 0 <= score <= 100:
            raise forms.ValidationError('Enter a score from 0 to 100.')
        return score

    def clean(self):
        cleaned = super().clean()
        for field in ('first_term_score', 'second_term_score', 'third_term_score'):
            score = cleaned.get(field)
            if score is not None and not 0 <= score <= 100:
                self.add_error(field, 'Enter a score from 0 to 100.')
        if not any(cleaned.get(field) is not None for field in ('score', 'first_term_score', 'second_term_score', 'third_term_score')):
            raise forms.ValidationError('Enter at least one assessment or term score.')
        return cleaned


class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ('name', 'start_date', 'end_date', 'terms', 'is_active')
        widgets = {'start_date': forms.DateInput(attrs={'type': 'date'}), 'end_date': forms.DateInput(attrs={'type': 'date'})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('start_date') and cleaned.get('end_date') and cleaned['end_date'] <= cleaned['start_date']:
            self.add_error('end_date', 'The end date must be after the start date.')
        return cleaned


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ('name', 'code', 'school_class', 'teacher', 'subject_type')


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ('title', 'subject', 'school_class', 'due_date', 'status', 'instructions')
        widgets = {
            'subject': forms.Select(attrs={'class': 'subject-select'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'instructions': forms.Textarea(attrs={'rows': 3}),
        }


class FinancialTransactionForm(forms.ModelForm):
    class Meta:
        model = FinancialTransaction
        fields = ('name', 'transaction_date', 'amount', 'transaction_type', 'note')
        widgets = {'transaction_date': forms.DateInput(attrs={'type': 'date'}), 'note': forms.Textarea(attrs={'rows': 3})}


class ModuleRecordForm(forms.ModelForm):
    class Meta:
        model = ModuleRecord
        fields = ('title', 'reference', 'status', 'record_date', 'amount', 'details')
        widgets = {'record_date': forms.DateInput(attrs={'type': 'date'}), 'details': forms.Textarea(attrs={'rows': 4})}


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ('title', 'body', 'is_pinned')
        widgets = {'body': forms.Textarea(attrs={'rows': 7, 'placeholder': 'Write the full announcement here…'})}


class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = ParentProfile
        fields = ('first_name', 'last_name', 'gender', 'occupation', 'parent_id', 'blood_group', 'religion', 'email', 'address', 'phone', 'ward', 'bio')
        widgets = {'bio': forms.Textarea(attrs={'rows': 4})}


class LibraryBookForm(forms.ModelForm):
    class Meta:
        model = LibraryBook
        fields = ('title', 'author', 'isbn', 'category', 'publication_year', 'description', 'cover_image', 'reading_file')
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}
        help_texts = {
            'reading_file': 'Upload a PDF or EPUB file that readers can open in the library.',
            'cover_image': 'Optional: upload a JPG, PNG, or WebP book cover.',
        }

    def clean_reading_file(self):
        book_file = self.cleaned_data['reading_file']
        if book_file.size > 25 * 1024 * 1024:
            raise forms.ValidationError('The book file must be smaller than 25 MB.')
        if not book_file.name.lower().endswith(('.pdf', '.epub')):
            raise forms.ValidationError('Upload a PDF or EPUB book file.')
        return book_file


class UserProfileForm(ProfilePhotoValidationMixin, forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('profile_photo',)
