import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('management', '0002_graderecord'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name='AcademicYear', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('name', models.CharField(max_length=20)), ('start_date', models.DateField()), ('end_date', models.DateField()), ('terms', models.PositiveSmallIntegerField(default=3)), ('is_active', models.BooleanField(default=False)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-start_date']}),
        migrations.CreateModel(name='FinancialTransaction', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('name', models.CharField(max_length=150)), ('transaction_date', models.DateField()), ('amount', models.DecimalField(decimal_places=2, max_digits=12)), ('transaction_type', models.CharField(choices=[('income', 'Income'), ('expense', 'Expense')], max_length=10)), ('note', models.TextField(blank=True)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-transaction_date', '-created_at']}),
        migrations.CreateModel(name='Subject', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('name', models.CharField(max_length=100)), ('code', models.CharField(max_length=30)), ('subject_type', models.CharField(choices=[('core', 'Core'), ('elective', 'Elective')], default='core', max_length=12)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('school_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subjects', to='management.schoolclass')), ('teacher', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subjects', to='management.teacher')),
        ], options={'ordering': ['name']}),
        migrations.CreateModel(name='Assignment', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('title', models.CharField(max_length=150)), ('due_date', models.DateField()), ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=10)), ('instructions', models.TextField(blank=True)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('school_class', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignments', to='management.schoolclass')), ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='management.subject')),
        ], options={'ordering': ['due_date']}),
        migrations.AddConstraint(model_name='academicyear', constraint=models.UniqueConstraint(fields=('created_by', 'name'), name='unique_academic_year_name')),
        migrations.AddConstraint(model_name='subject', constraint=models.UniqueConstraint(fields=('created_by', 'code'), name='unique_subject_code')),
    ]
