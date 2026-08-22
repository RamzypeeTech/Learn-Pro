from django.contrib import admin
from .models import AcademicYear, Announcement, Assignment, AttendanceRecord, FeeRecord, FinancialTransaction, GradeRecord, LibraryBook, LoginActivity, Notification, ParentProfile, SchoolClass, SchoolEvent, Student, Subject, Teacher, UserProfile

admin.site.register([AcademicYear, SchoolClass, Teacher, Student, Subject, Assignment, AttendanceRecord, FeeRecord, SchoolEvent, GradeRecord, FinancialTransaction, ParentProfile, LibraryBook, UserProfile, Announcement, Notification, LoginActivity])
