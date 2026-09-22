import logging

from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking
from apps.common.exceptions import DomainError, NotFound

from .models import (
    REVIEW_WINDOW_DAYS, CustomerRating, ProviderReply, Review, ReviewEdit,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def create_review(*, booking_id, customer_id, rating, punctuality=None,
                  quality=None, professionalism=None, price_fairness=None,
                  comment=""):
    booking = (
        Booking.objects
        .select_for_update()
        .select_related("provider", "customer")
        .filter(pk=booking_id, customer_id=customer_id)
        .first()
    )
    if booking is None:
        raise NotFound("No such booking.", code="booking_not_found")

    if booking.state != Booking.State.COMPLETED:
        raise DomainError(
            "Only a completed booking can be reviewed.",
            code="booking_not_complete",
            details={"state": booking.state},
        )

    if Review.objects.filter(booking=booking).exists():
        raise DomainError("You have already reviewed this booking.",
                          code="already_reviewed")

    _assert_within_window(booking)

    review = Review.objects.create(
        booking=booking,
        customer_id=customer_id,
        provider=booking.provider,
        rating=rating,
        punctuality=punctuality,
        quality=quality,
        professionalism=professionalism,
        price_fairness=price_fairness,
        comment=comment,
        reveal_deadline=Review.default_reveal_deadline(),
    )

    _maybe_reveal(booking)
    logger.info("Review %s created for provider %s", review.id,
                booking.provider_id)
    return review


def _assert_within_window(booking):
    reference = booking.confirmed_at or booking.completed_at
    if reference is None:
        return

    deadline = reference + timezone.timedelta(days=REVIEW_WINDOW_DAYS)
    if timezone.now() > deadline:
        raise DomainError(
            "The %d-day review window for this booking has closed."
            % REVIEW_WINDOW_DAYS,
            code="review_window_closed",
        )


@transaction.atomic
def rate_customer(*, booking_id, provider_id, rating, comment=""):
    booking = (
        Booking.objects
        .select_for_update()
        .select_related("customer")
        .filter(pk=booking_id, provider_id=provider_id)
        .first()
    )
    if booking is None:
        raise NotFound("No such booking.", code="booking_not_found")

    if booking.state != Booking.State.COMPLETED:
        raise DomainError(
            "Only a completed booking can be rated.",
            code="booking_not_complete",
        )

    if CustomerRating.objects.filter(booking=booking).exists():
        raise DomainError("You have already rated this customer.",
                          code="already_rated")

    record = CustomerRating.objects.create(
        booking=booking,
        provider_id=provider_id,
        customer=booking.customer,
        rating=rating,
        comment=comment,
    )

    _maybe_reveal(booking)
    return record


def _maybe_reveal(booking):
    review = Review.objects.filter(booking=booking).first()
    rating = CustomerRating.objects.filter(booking=booking).first()

    if review is None or rating is None:
        return False

    now = timezone.now()
    if review.published_at is None:
        review.published_at = now
        review.save(update_fields=["published_at", "updated_at"])
        _recompute_trust(review.provider_id)
    if rating.published_at is None:
        rating.published_at = now
        rating.save(update_fields=["published_at", "updated_at"])
    return True


def reveal_expired_reviews(*, now=None):
    now = now or timezone.now()

    pending = Review.objects.filter(
        published_at__isnull=True, reveal_deadline__lte=now,
    )

    revealed = 0
    for review in pending.iterator():
        with transaction.atomic():
            locked = (
                Review.objects
                .select_for_update()
                .filter(pk=review.pk, published_at__isnull=True)
                .first()
            )
            if locked is None:
                continue

            locked.published_at = now
            locked.save(update_fields=["published_at", "updated_at"])
            _recompute_trust(locked.provider_id)
            revealed += 1

    CustomerRating.objects.filter(
        published_at__isnull=True,
        booking__review__reveal_deadline__lte=now,
    ).update(published_at=now)

    return revealed


@transaction.atomic
def edit_review(*, review_id, customer_id, rating=None, comment=None):
    review = (
        Review.objects
        .select_for_update()
        .filter(pk=review_id, customer_id=customer_id)
        .first()
    )
    if review is None:
        raise NotFound("No such review.", code="review_not_found")

    if not review.is_editable:
        raise DomainError(
            "A review cannot be edited more than 24 hours after posting.",
            code="edit_window_closed",
        )

    ReviewEdit.objects.create(
        review=review,
        previous_rating=review.rating,
        previous_comment=review.comment,
    )

    if rating is not None:
        review.rating = rating
    if comment is not None:
        review.comment = comment
    review.edit_count += 1
    review.save(update_fields=["rating", "comment", "edit_count",
                               "updated_at"])

    if review.is_published:
        _recompute_trust(review.provider_id)
    return review


@transaction.atomic
def reply_to_review(*, review_id, provider_id, body):
    review = Review.objects.filter(pk=review_id,
                                   provider_id=provider_id).first()
    if review is None:
        raise NotFound("No such review.", code="review_not_found")

    if not review.is_published:
        raise DomainError(
            "You cannot reply before the review is published.",
            code="review_not_published",
        )

    if ProviderReply.objects.filter(review=review).exists():
        raise DomainError("You have already replied to this review.",
                          code="already_replied")

    if not body:
        raise DomainError("A reply needs a body.", code="body_required")

    return ProviderReply.objects.create(
        review=review, provider_id=provider_id, body=body,
    )


@transaction.atomic
def hide_review(*, review_id, admin_user_id, reason):
    review = Review.objects.select_for_update().filter(pk=review_id).first()
    if review is None:
        raise NotFound("No such review.", code="review_not_found")

    if not reason:
        raise DomainError("Hiding a review needs a reason.",
                          code="reason_required")

    review.is_hidden = True
    review.hidden_reason = reason
    review.hidden_by_id = admin_user_id
    review.hidden_at = timezone.now()
    review.save(update_fields=["is_hidden", "hidden_reason", "hidden_by",
                               "hidden_at", "updated_at"])

    _recompute_trust(review.provider_id)
    logger.info("Review %s hidden by admin %s", review_id, admin_user_id)
    return review


@transaction.atomic
def unhide_review(*, review_id, admin_user_id):
    review = Review.objects.select_for_update().filter(pk=review_id).first()
    if review is None:
        raise NotFound("No such review.", code="review_not_found")

    review.is_hidden = False
    review.hidden_reason = ""
    review.hidden_by_id = admin_user_id
    review.hidden_at = timezone.now()
    review.save(update_fields=["is_hidden", "hidden_reason", "hidden_by",
                               "hidden_at", "updated_at"])

    _recompute_trust(review.provider_id)
    return review


def _recompute_trust(provider_id):
    from apps.trust import engine
    from apps.trust.models import TrustSnapshot

    transaction.on_commit(
        lambda: engine.recompute(
            provider_id, trigger=TrustSnapshot.Trigger.REVIEW_CHANGED,
        )
    )
