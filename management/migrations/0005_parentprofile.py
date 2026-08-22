import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('management', '0004_modulerecord'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='ParentProfile', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('created_at', models.DateTimeField(auto_now_add=True)), ('first_name', models.CharField(max_length=70)), ('last_name', models.CharField(max_length=70)), ('parent_id', models.CharField(max_length=40)), ('gender', models.CharField(choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], max_length=10)), ('occupation', models.CharField(blank=True, max_length=100)), ('blood_group', models.CharField(blank=True, max_length=4)), ('religion', models.CharField(blank=True, max_length=40)), ('email', models.EmailField(blank=True, max_length=254)), ('phone', models.CharField(max_length=30)), ('address', models.CharField(blank=True, max_length=255)), ('bio', models.TextField(blank=True)), ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)), ('ward', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='parents', to='management.student')),
    ], options={'ordering': ['first_name', 'last_name']}), migrations.AddConstraint(model_name='parentprofile', constraint=models.UniqueConstraint(fields=('created_by', 'parent_id'), name='unique_parent_id'))]
