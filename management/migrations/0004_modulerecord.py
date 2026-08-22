import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('management', '0003_academicyear_financialtransaction_subject_assignment'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='ModuleRecord', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('module', models.CharField(max_length=30)), ('title', models.CharField(max_length=160)), ('reference', models.CharField(blank=True, max_length=120)), ('status', models.CharField(blank=True, max_length=40)), ('record_date', models.DateField(blank=True, null=True)), ('amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)), ('details', models.TextField(blank=True)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
    ], options={'ordering': ['-record_date', '-created_at']})]
