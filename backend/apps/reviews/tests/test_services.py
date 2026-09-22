import pytest
from django.utils import timezone

from apps.bookings.models import Booking
from apps.common.exceptions import DomainError, NotFound
from apps.reviews import services
from apps.reviews.models import (
    CustomerRating, ProviderReply, Review, ReviewEdit,
)
from apps.trust import engine
from apps.trust.models import TrustSnapshot

pytestmark = pytest.mark.django_db


def test_review_requires_a_completed_booking(customer, provider, service,
                                             dhanmondi):
    from apps.bookings import services as booking_services

    start = timezone.now() + timezone.timedelta(days=2)
    request = booking_services.create_request(
        customer_id=customer.id, service_id=service.id,
        location_id=dhanmondi.id, address="x", description="y",
        preferred_start=start,
        preferred_end=start + timezone.timedelta(hours=2),
    )
    booking = booking_services.respond_to_request(
        request_id=request.id, provider_id=provider.id, accept=True,
    )

    with pytest.raises(DomainError) as exc:
        services.create_review(booking_id=booking.id,
                               customer_id=customer.id, rating=5)
    assert exc.value.code == "booking_not_complete"


def test_review_created_on_completed_booking(customer, completed_booking):
    review = services.create_review(
        booking_id=completed_booking.id, customer_id=customer.id,
        rating=5, punctuality=5, quality=4, professionalism=5,
        price_fairness=4, comment="Quick and tidy.",
    )
    assert review.rating == 5
    assert review.quality == 4


def test_only_one_review_per_booking(customer, completed_booking):
    services.create_review(booking_id=completed_booking.id,
                           customer_id=customer.id, rating=5)
    with pytest.raises(DomainError) as exc:
        services.create_review(booking_id=completed_booking.id,
                               customer_id=customer.id, rating=1)
    assert exc.value.code == "already_reviewed"


def test_another_customer_cannot_review_the_booking(completed_booking, db):
    from apps.accounts import services as account_services
    from apps.accounts.models import User

    other = account_services.register_user(
        phone="+8801999999999", password="testpass123",
        role=User.Role.CUSTOMER,
    ).customer_profile

    with pytest.raises(NotFound):
        services.create_review(booking_id=completed_booking.id,
                               customer_id=other.id, rating=1)


def test_review_window_closes_after_thirty_days(customer,
                                                completed_booking):
    Booking.objects.filter(pk=completed_booking.id).update(
        confirmed_at=timezone.now() - timezone.timedelta(days=31),
    )
    with pytest.raises(DomainError) as exc:
        services.create_review(booking_id=completed_booking.id,
                               customer_id=customer.id, rating=5)
    assert exc.value.code == "review_window_closed"


def test_review_is_not_published_until_both_sides_submit(customer, provider,
                                                          completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    assert review.is_published is False
    assert review.published_at is None


def test_both_sides_submitting_reveals_both(customer, provider,
                                            completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    services.rate_customer(booking_id=completed_booking.id,
                           provider_id=provider.id, rating=4)

    review.refresh_from_db()
    rating = CustomerRating.objects.get(booking=completed_booking)
    assert review.is_published is True
    assert rating.published_at is not None


def test_provider_rating_first_also_works(customer, provider,
                                          completed_booking):
    services.rate_customer(booking_id=completed_booking.id,
                           provider_id=provider.id, rating=4)
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)

    review.refresh_from_db()
    assert review.is_published is True


def test_reveal_after_deadline_without_the_other_side(customer,
                                                      completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    Review.objects.filter(pk=review.id).update(
        reveal_deadline=timezone.now() - timezone.timedelta(minutes=1),
    )

    assert services.reveal_expired_reviews() == 1
    review.refresh_from_db()
    assert review.is_published is True


def test_reveal_is_idempotent(customer, completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    Review.objects.filter(pk=review.id).update(
        reveal_deadline=timezone.now() - timezone.timedelta(minutes=1),
    )
    assert services.reveal_expired_reviews() == 1
    assert services.reveal_expired_reviews() == 0


def test_unpublished_review_does_not_move_trust(customer, provider,
                                                completed_booking):
    before = engine.recompute(provider.id).score
    services.create_review(booking_id=completed_booking.id,
                           customer_id=customer.id, rating=1)
    after = engine.recompute(provider.id).score
    assert after == before


def test_published_review_moves_trust(customer, provider, completed_booking,
                                      django_capture_on_commit_callbacks):
    before = engine.recompute(provider.id).score

    services.create_review(booking_id=completed_booking.id,
                           customer_id=customer.id, rating=5)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)

    after = engine.recompute(provider.id).score
    assert after > before


def test_bad_review_lowers_trust(customer, provider, completed_booking,
                                 django_capture_on_commit_callbacks):
    before = engine.recompute(provider.id).score

    services.create_review(booking_id=completed_booking.id,
                           customer_id=customer.id, rating=1)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)

    after = engine.recompute(provider.id).score
    assert after < before


def test_review_recompute_records_its_trigger(
        customer, provider, completed_booking,
        django_capture_on_commit_callbacks):
    services.create_review(booking_id=completed_booking.id,
                           customer_id=customer.id, rating=5)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)

    assert TrustSnapshot.objects.filter(
        provider=provider,
        trigger=TrustSnapshot.Trigger.REVIEW_CHANGED,
    ).exists()


def test_hidden_review_is_excluded_from_trust(
        customer, provider, admin_user, completed_booking,
        django_capture_on_commit_callbacks):
    services.create_review(booking_id=completed_booking.id,
                           customer_id=customer.id, rating=1)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)

    with_review = engine.recompute(provider.id).score

    review = Review.objects.get(booking=completed_booking)
    with django_capture_on_commit_callbacks(execute=True):
        services.hide_review(review_id=review.id,
                             admin_user_id=admin_user.id,
                             reason="Abusive language")

    without_review = engine.recompute(provider.id).score
    assert without_review > with_review


def test_hiding_requires_a_reason(customer, admin_user, completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=1)
    with pytest.raises(DomainError) as exc:
        services.hide_review(review_id=review.id,
                             admin_user_id=admin_user.id, reason="")
    assert exc.value.code == "reason_required"


def test_unhiding_restores_the_review(customer, provider, admin_user,
                                      completed_booking,
                                      django_capture_on_commit_callbacks):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)
        services.hide_review(review_id=review.id,
                             admin_user_id=admin_user.id, reason="Mistake")
        services.unhide_review(review_id=review.id,
                               admin_user_id=admin_user.id)

    review.refresh_from_db()
    assert review.is_hidden is False


def test_edit_within_the_window_keeps_history(customer, completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=2,
                                    comment="Slow")
    services.edit_review(review_id=review.id, customer_id=customer.id,
                         rating=4, comment="Slow but thorough")

    review.refresh_from_db()
    assert review.rating == 4
    assert review.edit_count == 1

    history = ReviewEdit.objects.get(review=review)
    assert history.previous_rating == 2
    assert history.previous_comment == "Slow"


def test_edit_rejected_after_twenty_four_hours(customer, completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=2)
    Review.objects.filter(pk=review.id).update(
        created_at=timezone.now() - timezone.timedelta(hours=25),
    )

    with pytest.raises(DomainError) as exc:
        services.edit_review(review_id=review.id, customer_id=customer.id,
                             rating=5)
    assert exc.value.code == "edit_window_closed"


def test_edit_history_is_append_only(customer, completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=2)
    services.edit_review(review_id=review.id, customer_id=customer.id,
                         rating=4)

    history = ReviewEdit.objects.get(review=review)
    history.previous_rating = 5
    with pytest.raises(ValueError):
        history.save()
    with pytest.raises(ValueError):
        history.delete()


def test_provider_replies_once(customer, provider, completed_booking,
                               django_capture_on_commit_callbacks):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)

    services.reply_to_review(review_id=review.id, provider_id=provider.id,
                             body="Thank you!")

    with pytest.raises(DomainError) as exc:
        services.reply_to_review(review_id=review.id,
                                 provider_id=provider.id, body="Again")
    assert exc.value.code == "already_replied"


def test_provider_cannot_reply_before_publication(customer, provider,
                                                   completed_booking):
    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    with pytest.raises(DomainError) as exc:
        services.reply_to_review(review_id=review.id,
                                 provider_id=provider.id, body="Thanks")
    assert exc.value.code == "review_not_published"


def test_provider_cannot_reply_to_someone_elses_review(
        customer, provider, completed_booking, service, dhanmondi, db,
        django_capture_on_commit_callbacks):
    from apps.accounts import services as account_services
    from apps.accounts.models import User

    review = services.create_review(booking_id=completed_booking.id,
                                    customer_id=customer.id, rating=5)
    with django_capture_on_commit_callbacks(execute=True):
        services.rate_customer(booking_id=completed_booking.id,
                               provider_id=provider.id, rating=5)

    stranger = account_services.register_user(
        phone="+8801888888888", password="testpass123",
        role=User.Role.PROVIDER,
    ).provider_profile

    with pytest.raises(NotFound):
        services.reply_to_review(review_id=review.id,
                                 provider_id=stranger.id, body="Hello")


def test_customer_rating_requires_completed_booking(provider, customer,
                                                    service, dhanmondi):
    from apps.bookings import services as booking_services

    start = timezone.now() + timezone.timedelta(days=2)
    request = booking_services.create_request(
        customer_id=customer.id, service_id=service.id,
        location_id=dhanmondi.id, address="x", description="y",
        preferred_start=start,
        preferred_end=start + timezone.timedelta(hours=2),
    )
    booking = booking_services.respond_to_request(
        request_id=request.id, provider_id=provider.id, accept=True,
    )

    with pytest.raises(DomainError) as exc:
        services.rate_customer(booking_id=booking.id,
                               provider_id=provider.id, rating=5)
    assert exc.value.code == "booking_not_complete"
