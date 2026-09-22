import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import CustomerProfile, ProviderProfile
from apps.catalogue.models import Location, Service
from apps.common.models import AppendOnlyModel, TimeStampedModel

REQUEST_EXPIRY_HOURS = 24
AUTO_CONFIRM_HOURS = 72


def request_photo_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return "requests/%s/%s.%s" % (
        instance.request_id, uuid.uuid4().hex, extension,
    )


class ServiceRequest(TimeStampedModel):
    class State(models.TextChoices):
        OPEN = "open", _("Open")
        ACCEPTED = "accepted", _("Accepted")
        WITHDRAWN = "withdrawn", _("Withdrawn by customer")
        EXPIRED = "expired", _("Expired unanswered")

    class Kind(models.TextChoices):
        DIRECT = "direct", _("Directed at one provider")
        BROADCAST = "broadcast", _("Broadcast to the area")

    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.PROTECT, related_name="requests",
    )
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name="requests",
    )
    location = models.ForeignKey(
        Location, on_delete=models.PROTECT, related_name="requests",
    )
    address = models.TextField()
    description = models.TextField()

    kind = models.CharField(max_length=20, choices=Kind.choices,
                            default=Kind.BROADCAST)
    target_provider = models.ForeignKey(
        ProviderProfile, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="direct_requests",
    )

    preferred_start = models.DateTimeField()
    preferred_end = models.DateTimeField()

    state = models.CharField(max_length=20, choices=State.choices,
                             default=State.OPEN, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(preferred_end__gt=models.F(
                    "preferred_start")),
                name="request_window_ordered",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(kind="broadcast")
                    | models.Q(target_provider__isnull=False)
                ),
                name="direct_request_needs_target",
            ),
        ]
        indexes = [
            models.Index(fields=["state", "expires_at"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["service", "location", "state"]),
        ]

    def __str__(self):
        return "Request #%s %s" % (self.pk, self.service.name)

    @property
    def is_open(self):
        return self.state == self.State.OPEN

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @staticmethod
    def default_expiry():
        return timezone.now() + timezone.timedelta(hours=REQUEST_EXPIRY_HOURS)


class RequestPhoto(TimeStampedModel):
    MAX_PER_REQUEST = 5

    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="photos",
    )
    image = models.ImageField(upload_to=request_photo_path)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return "Photo for request #%s" % self.request_id


class ProviderResponse(TimeStampedModel):
    class Decision(models.TextChoices):
        ACCEPTED = "accepted", _("Accepted")
        DECLINED = "declined", _("Declined")

    request = models.ForeignKey(
        ServiceRequest, on_delete=models.CASCADE, related_name="responses",
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE,
        related_name="request_responses",
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    reason = models.TextField(blank=True)
    response_seconds = models.PositiveIntegerField()

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "provider"],
                name="one_response_per_provider_per_request",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "-created_at"]),
        ]

    def __str__(self):
        return "%s %s request #%s" % (
            self.provider.display_name, self.decision, self.request_id,
        )


class Booking(TimeStampedModel):
    class State(models.TextChoices):
        SCHEDULED = "scheduled", _("Scheduled")
        IN_PROGRESS = "in_progress", _("In progress")
        AWAITING_CONFIRM = "awaiting_confirm", _("Awaiting confirmation")
        COMPLETED = "completed", _("Completed")
        CANCELLED_CUSTOMER = "cancelled_customer", _("Cancelled by customer")
        CANCELLED_PROVIDER = "cancelled_provider", _("Cancelled by provider")
        DISPUTED = "disputed", _("Disputed")

    TERMINAL_STATES = {
        State.COMPLETED, State.CANCELLED_CUSTOMER,
        State.CANCELLED_PROVIDER, State.DISPUTED,
    }

    request = models.OneToOneField(
        ServiceRequest, on_delete=models.PROTECT, related_name="booking",
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.PROTECT, related_name="bookings",
    )
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.PROTECT, related_name="bookings",
    )

    state = models.CharField(max_length=30, choices=State.choices,
                             default=State.SCHEDULED, db_index=True)
    scheduled_for = models.DateTimeField(db_index=True)

    agreed_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    final_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )
    customer_confirmed_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    accepted_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    cancelled_by = models.CharField(max_length=20, blank=True)
    cancel_reason = models.TextField(blank=True)
    customer_confirmed_cancellation = models.BooleanField(default=False)
    was_no_show = models.BooleanField(default=False)
    auto_confirmed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "state"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["state", "completed_at"]),
            models.Index(fields=["state", "scheduled_for"]),
        ]

    def __str__(self):
        return "Booking #%s (%s)" % (self.pk, self.state)

    @property
    def is_terminal(self):
        return self.state in self.TERMINAL_STATES

    @property
    def is_cancelled(self):
        return self.state in {
            self.State.CANCELLED_CUSTOMER, self.State.CANCELLED_PROVIDER,
        }

    @property
    def notice_hours(self):
        if self.cancelled_at is None:
            return None
        delta = self.scheduled_for - self.cancelled_at
        return max(delta.total_seconds() / 3600.0, 0.0)

    @property
    def price_mismatch(self):
        if self.final_price is None or self.customer_confirmed_price is None:
            return False
        return self.final_price != self.customer_confirmed_price


class BookingEvent(AppendOnlyModel):
    class Actor(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        PROVIDER = "provider", _("Provider")
        ADMIN = "admin", _("Admin")
        SYSTEM = "system", _("System")

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="events",
    )
    from_state = models.CharField(max_length=30, blank=True)
    to_state = models.CharField(max_length=30)
    actor = models.CharField(max_length=20, choices=Actor.choices)
    actor_user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="booking_events",
    )
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["booking", "created_at"]),
        ]

    def __str__(self):
        return "#%s %s -> %s by %s" % (
            self.booking_id, self.from_state or "new", self.to_state,
            self.actor,
        )
