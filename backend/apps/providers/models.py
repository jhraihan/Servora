import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import ProviderProfile
from apps.catalogue.models import Location, Service
from apps.common.models import TimeStampedModel
from apps.common.storage import private_storage


CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "pdf": "application/pdf",
}


def verification_document_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return "verification/%s/%s.%s" % (
        instance.provider_id, uuid.uuid4().hex, extension,
    )


def work_photo_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return "work_photos/%s/%s.%s" % (
        instance.provider_id, uuid.uuid4().hex, extension,
    )


class ProviderService(TimeStampedModel):
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE, related_name="offerings",
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="provider_offerings",
    )

    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    estimated_duration_minutes = models.PositiveIntegerField(null=True,
                                                             blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("provider service")
        ordering = ["service__category__display_order", "service__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "service"],
                name="provider_service_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["service", "is_active"]),
            models.Index(fields=["provider", "is_active"]),
        ]

    def __str__(self):
        return "%s: %s" % (self.provider.display_name, self.service.name)

    @property
    def price_flag(self):
        return self.service.price_flag(self.price)


class ServiceArea(TimeStampedModel):
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE, related_name="service_areas",
    )
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="providers",
    )
    travel_surcharge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        verbose_name = _("service area")
        ordering = ["location__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "location"],
                name="provider_location_unique",
            ),
        ]
        indexes = [models.Index(fields=["location", "provider"])]

    def __str__(self):
        return "%s serves %s" % (self.provider.display_name, self.location)


class Availability(TimeStampedModel):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, _("Monday")
        TUESDAY = 1, _("Tuesday")
        WEDNESDAY = 2, _("Wednesday")
        THURSDAY = 3, _("Thursday")
        FRIDAY = 4, _("Friday")
        SATURDAY = 5, _("Saturday")
        SUNDAY = 6, _("Sunday")

    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE, related_name="availability",
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name_plural = _("availability")
        ordering = ["weekday", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="availability_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["provider", "weekday", "start_time"],
                name="availability_window_unique",
            ),
        ]
        indexes = [models.Index(fields=["provider", "weekday"])]

    def __str__(self):
        return "%s %s %s-%s" % (
            self.provider.display_name, self.get_weekday_display(),
            self.start_time, self.end_time,
        )

    def overlaps(self, other_start, other_end):
        return self.start_time < other_end and other_start < self.end_time


class AvailabilityException(TimeStampedModel):
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE,
        related_name="availability_exceptions",
    )
    date = models.DateField()
    is_available = models.BooleanField(default=False)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "date"],
                name="availability_exception_unique_per_day",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(is_available=False)
                    | models.Q(start_time__isnull=False,
                               end_time__isnull=False)
                ),
                name="availability_exception_hours_required_when_available",
            ),
        ]
        indexes = [models.Index(fields=["provider", "date"])]

    def __str__(self):
        state = "available" if self.is_available else "unavailable"
        return "%s %s on %s" % (self.provider.display_name, state, self.date)


class VerificationDocument(TimeStampedModel):
    class DocumentType(models.TextChoices):
        NID_FRONT = "nid_front", _("NID front")
        NID_BACK = "nid_back", _("NID back")
        TRADE_CERTIFICATE = "trade_certificate", _("Trade certificate")
        ADDRESS_PROOF = "address_proof", _("Address proof")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending review")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")

    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE,
        related_name="verification_documents",
    )
    document_type = models.CharField(max_length=30,
                                     choices=DocumentType.choices)
    file = models.FileField(upload_to=verification_document_path,
                            storage=private_storage)

    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    purge_after = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["provider", "document_type"]),
        ]

    def __str__(self):
        return "%s %s (%s)" % (
            self.provider.display_name, self.get_document_type_display(),
            self.status,
        )

    @property
    def is_reviewed(self):
        return self.status != self.Status.PENDING

    @property
    def file_basename(self):
        return self.file.name.rsplit("/", 1)[-1]

    @property
    def content_type(self):
        extension = self.file.name.rsplit(".", 1)[-1].lower()
        return CONTENT_TYPES.get(extension, "application/octet-stream")


class WorkPhoto(TimeStampedModel):
    MAX_PER_PROVIDER = 10

    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE, related_name="work_photos",
    )
    image = models.ImageField(upload_to=work_photo_path)
    caption = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "created_at"]
        indexes = [models.Index(fields=["provider", "display_order"])]

    def __str__(self):
        return "Photo for %s" % self.provider.display_name
