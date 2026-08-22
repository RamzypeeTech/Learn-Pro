from .models import Notification, UserProfile


NAVIGATION_ITEMS = [
    ('index', 'dashboard', 'DB', 'Dashboard'),
    ('academic_years', 'years', 'YR', 'Academic Years'),
    ('classes', 'classes', 'CL', 'Classes'),
    ('teachers', 'teachers', 'TR', 'Teachers'),
    ('students', 'students', 'ST', 'Students'),
    ('subjects', 'subjects', 'SU', 'Subjects'),
    ('attendance', 'attendance', 'AT', 'Attendance'),
    ('exams_results', 'events', 'EX', 'Exams & Results'),
    ('results', 'grades', 'RS', 'Results'),
    ('assignments', 'assignments', 'AS', 'Assignments'),
    ('fees', 'fees', 'FE', 'Fees'),
    ('financial_management', 'finance', 'FM', 'Financial Management'),
    ('announcements', 'announcements', 'AN', 'Announcements'),
    ('parents', 'parents', 'PR', 'Parent Portal'),
    ('messages', 'messages', 'MS', 'Messages'),
    ('timetable', 'timetable', 'TT', 'Timetable'),
    ('transport', 'transport', 'TP', 'Transport'),
    ('library', 'library', 'LB', 'Library'),
    ('hr_payroll', 'hr_payroll', 'HR', 'HR & Payroll'),
    ('system_settings', 'system_settings', 'SS', 'System Settings'),
    ('reports', 'reports', 'RP', 'Reports'),
]

ROLE_NAVIGATION = {role: {item[0] for item in NAVIGATION_ITEMS} for role, _ in UserProfile.ROLE_CHOICES}


def current_profile(request):
    if not request.user.is_authenticated:
        return {}
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    header_photo = profile.profile_photo
    if not header_photo:
        linked_record = profile.teacher or profile.student
        if linked_record:
            header_photo = linked_record.profile_photo
    allowed = ROLE_NAVIGATION.get(profile.role, set())
    navigation_items = [
        {'url_name': url_name, 'active': active, 'badge': badge, 'label': label}
        for url_name, active, badge, label in NAVIGATION_ITEMS if url_name in allowed
    ]
    return {'current_profile': profile, 'header_photo': header_photo, 'navigation_items': navigation_items, 'selected_academic_year': request.session.get('selected_academic_year', '2026-27'), 'unread_notification_count': Notification.objects.filter(user=request.user, is_read=False).count()}
