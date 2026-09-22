from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import CustomerProfile, ProviderProfile
from apps.bookings.models import Booking
from apps.common.models import AppendOnlyModel, TimeStampedModel

REVIEW_WINDOW_DAYS = 30
EDIT_WINDOW_HOURS = 24
REVEAL_WINDOW_DAYS = 14

RATING_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class Review(TimeStampedModel):
    booking = models.OneToOneField(
        Booking, on_delete=models.PROTECT, related_name="review",
    )
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.PROTECT, related_name="reviews",
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.PROTECT, related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField(validators=RATING_VALIDATORS)
    punctuality = models.PositiveSmallIntegerField(
        validators=RATING_VALIDATORS, null=True, blank=True,
    )
    quality = models.PositiveSmallIntegerField(
        validators=RATING_VALIDATORS, null=True, blank=True,
    )
    professionalism = models.PositiveSmallIntegerField(
        validators=RATING_VALIDATORS, null=True, blank=True,
    )
    price_fairness = models.PositiveSmallIntegerField(
        validators=RATING_VALIDATORS, null=True, blank=True,
    )

    comment = models.TextField(blank=True)

    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    reveal_deadline = models.DateTimeField(db_index=True)

    is_hidden = models.BooleanField(default=False, db_index=True)
    hidden_reason = models.TextField(blank=True)
    hidden_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hidden_reviews",
    )
    hidden_at = models.DateTimeField(null=True, blank=True)

    edit_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_in_range",
            ),
        ]
        indexes = [
            models.Index(fields=["provider", "-created_at"]),
            models.Index(fields=["provider", "is_hidden", "published_at"]),
            models.Index(fields=["published_at", "reveal_deadline"]),
        ]

    def __str__(self):
        return "Review #%s of %s: %s" % (
            self.pk, self.provider.display_name, self.rating,
        )

    @property
    def is_published(self):
        return self.published_at is not None

    @property
    def counts_toward_trust(self):
        return not self.is_hidden

    @property
    def is_editable(self):
        if self.created_at is None:
            return True
        age = timezone.now() - self.created_at
        return age.total_seconds() < EDIT_WINDOW_HOURS * 3600

    @staticmethod
    def default_reveal_deadline():
        return timezone.now() + timezone.timedelta(days=REVEAL_WINDOW_DAYS)


class ReviewEdit(AppendOnlyModel):
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name="edits",
    )
    previous_rating = models.PositiveSmallIntegerField()
    previous_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return "Edit of review #%s" % self.review_id


class ProviderReply(TimeStampedModel):
    review = models.OneToOneField(
        Review, on_delete=models.CASCADE, related_name="reply",
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.CASCADE,
        related_name="review_replies",
    )
    body = models.TextField()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return "Reply to review #%s" % self.review_id


class CustomerRating(TimeStampedModel):
    booking = models.OneToOneField(
        Booking, on_delete=models.PROTECT, related_name="customer_rating",
    )
    provider = models.ForeignKey(
        ProviderProfile, on_delete=models.PROTECT,
        related_name="ratings_given",
    )
    customer = models.ForeignKey(
        CustomerProfile, on_delete=models.PROTECT,
        related_name="ratings_received",
    )

    rating = models.PositiveSmallIntegerField(validators=RATING_VALIDATORS)
    comment = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "-created_at"]),
        ]

    def __str__(self):
        return "Rating of customer on booking #%s" % self.booking_id
