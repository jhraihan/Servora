
import apps.accounts.models
import apps.accounts.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('phone', models.CharField(blank=True, help_text='Canonical form +8801XXXXXXXXX.', max_length=14, null=True, unique=True, validators=[apps.accounts.validators.validate_bd_phone], verbose_name='phone number')),
                ('email', models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='email address')),
                ('full_name', models.CharField(blank=True, max_length=150, verbose_name='full name')),
                ('phone_verified', models.BooleanField(default=False)),
                ('email_verified', models.BooleanField(default=False)),
                ('active_role', models.CharField(choices=[('customer', 'Customer'), ('provider', 'Service Provider'), ('admin', 'Admin')], default='customer', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('suspended_at', models.DateTimeField(blank=True, null=True)),
                ('suspension_reason', models.TextField(blank=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', apps.accounts.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='CustomerProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('default_address', models.TextField(blank=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'customer profile',
            },
        ),
        migrations.CreateModel(
            name='PhoneOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('phone', models.CharField(db_index=True, max_length=14, validators=[apps.accounts.validators.validate_bd_phone])),
                ('code_hash', models.CharField(max_length=64)),
                ('purpose', models.CharField(choices=[('registration', 'Registration'), ('login', 'Login'), ('phone_change', 'Phone change')], default='registration', max_length=20)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'phone OTP',
                'indexes': [models.Index(fields=['phone', '-created_at'], name='accounts_ph_phone_ea13c2_idx')],
            },
        ),
        migrations.CreateModel(
            name='ProviderProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('display_name', models.CharField(max_length=120)),
                ('bio', models.TextField(blank=True)),
                ('experience_years', models.PositiveSmallIntegerField(default=0)),
                ('is_accepting_work', models.BooleanField(default=True)),
                ('identity_verified', models.BooleanField(default=False)),
                ('skill_verified', models.BooleanField(default=False)),
                ('address_verified', models.BooleanField(default=False)),
                ('trust_score', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('trust_tier', models.CharField(choices=[('new', 'New'), ('rising', 'Rising'), ('established', 'Established'), ('trusted_pro', 'Trusted Pro'), ('under_review', 'Under Review')], default='new', max_length=20)),
                ('trust_computed_at', models.DateTimeField(blank=True, null=True)),
                ('jobs_completed', models.PositiveIntegerField(default=0)),
                ('jobs_cancelled', models.PositiveIntegerField(default=0)),
                ('jobs_accepted', models.PositiveIntegerField(default=0)),
                ('requests_received', models.PositiveIntegerField(default=0)),
                ('median_response_seconds', models.PositiveIntegerField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='provider_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'provider profile',
            },
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['phone'], name='accounts_us_phone_f54457_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='accounts_us_email_74c8d6_idx'),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(condition=models.Q(('phone__isnull', False), ('email__isnull', False), _connector='OR'), name='user_has_phone_or_email'),
        ),
        migrations.AddIndex(
            model_name='providerprofile',
            index=models.Index(fields=['-trust_score'], name='accounts_pr_trust_s_54bc7a_idx'),
        ),
        migrations.AddIndex(
            model_name='providerprofile',
            index=models.Index(fields=['is_accepting_work', '-trust_score'], name='accounts_pr_is_acce_4c9b07_idx'),
        ),
    ]
