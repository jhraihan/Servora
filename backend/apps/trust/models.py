from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import ProviderProfile
from apps.common.models import AppendOnlyModel


class TrustSnapshot(AppendOnlyModel):
    class Trigger(models.TextChoices):
        BOOKING_COMPLETED = "booking_completed", _("Booking completed")
        BOOKING_CANCELLED = "booking_cancelled", _("Booking cancelled")
        REVIEW_CHANGED = "review_changed", _("Review created or changed")
        VERIFICATION_DECIDED = "verification_decided", _("Verification decided")
        DISPUTE_CHANGED = "dispute_changed", _("Dispute opened or resolved")
        NIGHTLY_BATCH = "nightly_batch", _("Nightly batch")
        MANUAL = "manual", _("Manual recomputation")

    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE, related_name="snapshots",
    )
    score = models.DecimalField(max_digits=5, decimal_places=2)
    tier = models.CharField(max_length=20)
    factors = models.JSONField()
    algo_version = models.CharField(max_length=10)
    trigger = models.CharField(max_length=40, choices=Trigger.choices)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "-created_at"]),
            models.Index(fields=["algo_version"]),
        ]

    def __str__(self):
        return "%s %s at %s" % (
            self.provider.display_name, self.score, self.created_at,
        )
