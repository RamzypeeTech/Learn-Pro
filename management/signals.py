from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Announcement, Assignment, AttendanceRecord, FeeRecord, FinancialTransaction, GradeRecord, LoginActivity, ModuleRecord, Notification, SchoolEvent, UserProfile


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


NOTIFIABLE_MODELS = (Announcement, Assignment, AttendanceRecord, FeeRecord, FinancialTransaction, GradeRecord, ModuleRecord, SchoolEvent)


def notify_workspace(sender, instance, created, **kwargs):
    """Create an in-app notification whenever school information is published."""
    if not created:
        return
    owner = instance.created_by
    title = 'New announcement' if isinstance(instance, Announcement) else f'New {sender._meta.verbose_name.replace("record", "").strip()}'
    description = getattr(instance, 'title', None) or getattr(instance, 'name', None) or getattr(instance, 'assessment_name', None) or 'A school record has been posted.'
    recipients = UserProfile.objects.filter(
        Q(user=owner) | Q(teacher__created_by=owner) | Q(student__created_by=owner) | Q(parent__created_by=owner)
    ).select_related('user').distinct()
    Notification.objects.bulk_create([
        Notification(user=profile.user, title=title, message=str(description), url='/announcements/' if isinstance(instance, Announcement) else '')
        for profile in recipients
        if profile.user_id != instance.created_by_id
    ])


for model in NOTIFIABLE_MODELS:
    post_save.connect(notify_workspace, sender=model, dispatch_uid=f'notify_{model.__name__}')
