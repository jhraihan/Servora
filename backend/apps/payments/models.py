from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import CustomerProfile, ProviderProfile
from apps.bookings.models import Booking
from apps.common.models import AppendOnlyModel, TimeStampedModel

CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def commission_for(amount, rate_percent):
    return money(Decimal(amount) * Decimal(rate_percent) / Decimal("100"))


class Payment(TimeStampedModel):
    class Method(models.TextChoices):
        CASH = "cash", _("Cash on completion")
        BKASH = "bkash", _("bKash")
        NAGAD = "nagad", _("Nagad")
        CARD = "card", _("Card")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SETTLED = "settled", _("Settled")
        FLAGGED = "flagged", _("Flagged for review")
        REFUNDED = "refunded", _("Refunded")

    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT, related_name="payments",
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.PROTECT, related_name="payments",
    )
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.PROTECT, related_name="payments",
    )

    method = models.CharField(max_length=20, choices=Method.choices,
                              default=Method.CASH)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.PENDING, db_index=True)

    provider_recorded_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    customer_confirmed_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    settled_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0"))],
    )

    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    settled_at = models.DateTimeField(null=True, blank=True)
    flagged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="resolved_payments",
    )
    resolution_note = models.TextField(blank=True)

    gateway = models.CharField(max_length=40, blank=True)
    gateway_reference = models.CharField(max_length=120, blank=True,
                                         db_index=True)
    gateway_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking"],
                condition=models.Q(method="cash"),
                name="one_cash_payment_per_booking",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["status", "flagged_at"]),
        ]

    def __str__(self):
        return "Payment #%s for booking #%s (%s)" % (
            self.pk, self.booking_id, self.status,
        )

    @property
    def amounts_match(self):
        return self.provider_recorded_amount == self.customer_confirmed_amount

    @property
    def net_amount(self):
        if self.settled_amount is None or self.commission_amount is None:
            return None
        return self.settled_amount - self.commission_amount


class LedgerEntry(AppendOnlyModel):
    class Kind(models.TextChoices):
        EARNING = "earning", _("Earning")
        COMMISSION = "commission", _("Platform commission")
        CASH_RETAINED = "cash_retained", _("Cash retained by provider")
        SETTLEMENT = "settlement", _("Provider settlement to platform")
        PAYOUT = "payout", _("Platform payout to provider")
        ADJUSTMENT = "adjustment", _("Adjustment")

    PER_BOOKING_KINDS = (Kind.EARNING, Kind.COMMISSION, Kind.CASH_RETAINED)

    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.PROTECT, related_name="ledger",
    )
    booking = models.ForeignKey(
        Booking, on_delete=models.PROTECT, null=True, blank=True,
        related_name="ledger_entries",
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True,
        related_name="ledger_entries",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ledger_entries_recorded",
    )
    reference = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = _("ledger entries")
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "kind"],
                condition=models.Q(kind__in=[
                    "earning", "commission", "cash_retained",
                ]),
                name="one_accrual_of_each_kind_per_booking",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "-created_at"]),
            models.Index(fields=["provider", "kind"]),
        ]

    def __str__(self):
        return "%s %s %s" % (self.provider.display_name, self.kind,
                             self.amount)
