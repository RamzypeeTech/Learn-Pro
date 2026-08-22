# Generated manually for School Pro's operational records.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='SchoolClass', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('name', models.CharField(max_length=80)), ('section', models.CharField(blank=True, max_length=30)), ('academic_year', models.CharField(default='2026-27', max_length=20)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['name', 'section']}),
        migrations.CreateModel(name='Teacher', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('full_name', models.CharField(max_length=120)), ('employee_id', models.CharField(max_length=40)), ('department', models.CharField(blank=True, max_length=80)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['full_name']}),
        migrations.CreateModel(name='Student', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('full_name', models.CharField(max_length=120)), ('student_id', models.CharField(max_length=40)), ('enrollment_date', models.DateField()), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('school_class', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='students', to='management.schoolclass')),
        ], options={'ordering': ['full_name']}),
        migrations.CreateModel(name='SchoolEvent', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('title', models.CharField(max_length=150)), ('event_type', models.CharField(default='School event', max_length=50)), ('scheduled_for', models.DateTimeField()), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('school_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='events', to='management.schoolclass')),
        ], options={'ordering': ['scheduled_for']}),
        migrations.CreateModel(name='FeeRecord', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('invoice_number', models.CharField(max_length=40)), ('amount_due', models.DecimalField(decimal_places=2, max_digits=12)), ('amount_paid', models.DecimalField(decimal_places=2, default=0, max_digits=12)), ('due_date', models.DateField()), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fee_records', to='management.student')),
        ], options={'ordering': ['due_date']}),
        migrations.CreateModel(name='AttendanceRecord', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('attendance_date', models.DateField()), ('status', models.CharField(choices=[('present', 'Present'), ('late', 'Late'), ('absent', 'Absent')], max_length=10)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_records', to='management.student')),
        ], options={'ordering': ['-attendance_date', 'student__full_name']}),
        migrations.AddConstraint(model_name='schoolclass', constraint=models.UniqueConstraint(fields=('created_by', 'name', 'section', 'academic_year'), name='unique_school_class')),
        migrations.AddConstraint(model_name='teacher', constraint=models.UniqueConstraint(fields=('created_by', 'employee_id'), name='unique_teacher_employee_id')),
        migrations.AddConstraint(model_name='student', constraint=models.UniqueConstraint(fields=('created_by', 'student_id'), name='unique_student_id')),
        migrations.AddConstraint(model_name='feerecord', constraint=models.UniqueConstraint(fields=('created_by', 'invoice_number'), name='unique_fee_invoice')),
        migrations.AddConstraint(model_name='attendancerecord', constraint=models.UniqueConstraint(fields=('student', 'attendance_date'), name='one_attendance_per_student_day')),
    ]
