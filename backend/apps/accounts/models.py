import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, \
    PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from .validators import normalise_bd_phone, validate_bd_phone

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone=None, email=None, password=None, **extra):
        if not phone and not email:
            raise ValueError("A user requires either a phone number or an "
                             "email address.")

        phone = normalise_bd_phone(phone) if phone else None
        email = self.normalize_email(email) if email else None

        user = self.model(phone=phone, email=email, **extra)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, phone=None, email=None, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(phone, email, password, **extra)

    def create_superuser(self, phone=None, email=None, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("phone_verified", True)

        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone, email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        PROVIDER = "provider", _("Service Provider")
        ADMIN = "admin", _("Admin")

    phone = models.CharField(
        _("phone number"), max_length=14, unique=True, null=True, blank=True,
        validators=[validate_bd_phone],
        help_text=_("Canonical form +8801XXXXXXXXX."),
    )
    email = models.EmailField(_("email address"), unique=True, null=True,
                              blank=True)
    full_name = models.CharField(_("full name"), max_length=150, blank=True)

    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    active_role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.CUSTOMER,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    suspended_at = models.DateTimeField(null=True, blank=True)
    suspension_reason = models.TextField(blank=True)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__isnull=False)
                | models.Q(email__isnull=False),
                name="user_has_phone_or_email",
            ),
        ]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.full_name or self.phone or self.email or f"user#{self.pk}"

    def clean(self):
        super().clean()
        if self.phone:
            self.phone = normalise_bd_phone(self.phone)
        if self.email:
            self.email = self.email.lower().strip()

    @property
    def is_suspended(self):
        return self.suspended_at is not None

    @property
    def roles(self):
        held = []
        if hasattr(self, "customer_profile"):
            held.append(self.Role.CUSTOMER)
        if hasattr(self, "provider_profile"):
            held.append(self.Role.PROVIDER)
        if self.is_staff:
            held.append(self.Role.ADMIN)
        return held

    def has_role(self, role):
        return role in self.roles

class CustomerProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    default_address = models.TextField(blank=True)

    class Meta:
        verbose_name = _("customer profile")

    def __str__(self):
        return f"Customer: {self.user}"

class ProviderProfile(TimeStampedModel):
    class Tier(models.TextChoices):
        NEW = "new", _("New")
        RISING = "rising", _("Rising")
        ESTABLISHED = "established", _("Established")
        TRUSTED_PRO = "trusted_pro", _("Trusted Pro")
        UNDER_REVIEW = "under_review", _("Under Review")

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="provider_profile",
    )
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    experience_years = models.PositiveSmallIntegerField(default=0)

    is_accepting_work = models.BooleanField(default=True)

    identity_verified = models.BooleanField(default=False)
    skill_verified = models.BooleanField(default=False)
    address_verified = models.BooleanField(default=False)

    trust_score = models.DecimalField(max_digits=5, decimal_places=2,
                                      default=0)
    trust_tier = models.CharField(max_length=20, choices=Tier.choices,
                                  default=Tier.NEW)
    trust_computed_at = models.DateTimeField(null=True, blank=True)

    jobs_completed = models.PositiveIntegerField(default=0)
    jobs_cancelled = models.PositiveIntegerField(default=0)
    jobs_accepted = models.PositiveIntegerField(default=0)
    requests_received = models.PositiveIntegerField(default=0)
    median_response_seconds = models.PositiveIntegerField(null=True,
                                                          blank=True)

    class Meta:
        verbose_name = _("provider profile")
        indexes = [
            models.Index(fields=["-trust_score"]),
            models.Index(fields=["is_accepting_work", "-trust_score"]),
        ]

    def __str__(self):
        return f"Provider: {self.display_name}"

    @property
    def phone_verified(self):
        return self.user.phone_verified

class PhoneOTP(TimeStampedModel):
    class Purpose(models.TextChoices):
        REGISTRATION = "registration", _("Registration")
        LOGIN = "login", _("Login")
        PHONE_CHANGE = "phone_change", _("Phone change")

    phone = models.CharField(max_length=14, db_index=True,
                             validators=[validate_bd_phone])
    code_hash = models.CharField(max_length=64)
    purpose = models.CharField(max_length=20, choices=Purpose.choices,
                               default=Purpose.REGISTRATION)

    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("phone OTP")
        indexes = [
            models.Index(fields=["phone", "-created_at"]),
        ]

    def __str__(self):
        return f"OTP {self.phone} ({self.purpose})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None

    @property
    def is_usable(self):
        return (
            not self.is_consumed
            and not self.is_expired
            and self.attempts < settings.OTP_MAX_VERIFY_ATTEMPTS
        )

    @staticmethod
    def generate_code():
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def hash_code(phone, code):
        import hashlib
        payload = f"{phone}:{code}:{settings.SECRET_KEY}".encode()
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def default_expiry(cls):
        return timezone.now() + timedelta(seconds=settings.OTP_TTL_SECONDS)

    def matches(self, code):
        return secrets.compare_digest(
            self.code_hash, self.hash_code(self.phone, code)
        )
