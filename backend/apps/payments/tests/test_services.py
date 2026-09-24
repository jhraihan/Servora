from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bookings import services as booking_services
from apps.bookings.models import Booking, BookingEvent
from apps.common.exceptions import DomainError
from apps.payments import selectors, services
from apps.payments.models import LedgerEntry, Payment, commission_for

pytestmark = pytest.mark.django_db

Kind = LedgerEntry.Kind


@pytest.mark.parametrize("amount,rate,expected", [
    ("2000.00", "12", "240.00"),
    ("1999.99", "12", "240.00"),
    ("1234.56", "12", "148.15"),
    ("0.30", "15", "0.05"),
    ("0.00", "12", "0.00"),
])
def test_commission_rounds_half_up_to_the_paisa(amount, rate, expected):
    assert commission_for(Decimal(amount), Decimal(rate)) == \
        Decimal(expected)


def test_completion_settles_a_cash_payment(complete_job):
    booking = complete_job(final_price="2000")
    payment = Payment.objects.get(booking=booking)

    assert payment.status == Payment.Status.SETTLED
    assert payment.method == Payment.Method.CASH
    assert payment.settled_amount == Decimal("2000.00")
    assert payment.commission_rate == Decimal("12.00")
    assert payment.commission_amount == Decimal("240.00")
    assert payment.net_amount == Decimal("1760.00")


def test_cash_job_writes_three_ledger_entries(complete_job):
    booking = complete_job(final_price="2000")
    entries = {e.kind: e.amount for e in
               LedgerEntry.objects.filter(booking=booking)}

    assert entries == {
        Kind.EARNING: Decimal("2000.00"),
        Kind.COMMISSION: Decimal("-240.00"),
        Kind.CASH_RETAINED: Decimal("-2000.00"),
    }


def test_cash_job_leaves_provider_owing_the_commission(complete_job,
                                                       provider):
    complete_job(final_price="2000")
    assert services.balance_for(provider.id) == Decimal("-240.00")
    assert services.outstanding_payable(provider.id) == Decimal("240.00")


def test_recording_twice_is_idempotent(complete_job):
    booking = complete_job(final_price="2000")
    first = Payment.objects.get(booking=booking)

    again = services.record_completion_payment(booking_id=booking.id)

    assert again.pk == first.pk
    assert Payment.objects.filter(booking=booking).count() == 1
    assert LedgerEntry.objects.filter(booking=booking).count() == 3


def test_database_rejects_a_duplicate_accrual(complete_job, provider):
    booking = complete_job(final_price="2000")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LedgerEntry.objects.create(provider=provider, booking=booking,
                                       kind=Kind.EARNING,
                                       amount=Decimal("2000"))


def test_database_rejects_a_second_cash_payment(complete_job, provider,
                                                customer):
    booking = complete_job(final_price="2000")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Payment.objects.create(
                booking=booking, provider=provider, customer=customer,
                method=Payment.Method.CASH,
                provider_recorded_amount=Decimal("1"),
                customer_confirmed_amount=Decimal("1"),
                commission_rate=Decimal("12"),
            )


def test_ledger_entries_are_append_only(complete_job):
    booking = complete_job(final_price="2000")
    entry = LedgerEntry.objects.filter(booking=booking).first()

    entry.amount = Decimal("1")
    with pytest.raises(ValueError):
        entry.save()
    with pytest.raises(ValueError):
        entry.delete()


def test_mismatch_is_flagged_and_kept_out_of_the_ledger(complete_job,
                                                       provider):
    booking = complete_job(final_price="2500", confirmed_price="2000")
    payment = Payment.objects.get(booking=booking)

    assert payment.status == Payment.Status.FLAGGED
    assert payment.flagged_at is not None
    assert payment.settled_amount is None
    assert not LedgerEntry.objects.filter(booking=booking).exists()
    assert services.balance_for(provider.id) == Decimal("0.00")


def test_mismatch_does_not_block_completion(complete_job):
    booking = complete_job(final_price="2500", confirmed_price="2000")
    booking.refresh_from_db()
    assert booking.state == Booking.State.COMPLETED


def test_admin_resolves_a_flagged_payment(complete_job, admin_user,
                                          provider):
    booking = complete_job(final_price="2500", confirmed_price="2000")
    payment = Payment.objects.get(booking=booking)

    resolved = services.resolve_flagged_payment(
        payment_id=payment.id, admin_user_id=admin_user.id,
        settled_amount=Decimal("2200"),
        note="Receipt photo shows 2200.",
    )

    assert resolved.status == Payment.Status.SETTLED
    assert resolved.settled_amount == Decimal("2200.00")
    assert resolved.commission_amount == Decimal("264.00")
    assert resolved.resolved_by_id == admin_user.id
    assert services.outstanding_payable(provider.id) == Decimal("264.00")

    earning = LedgerEntry.objects.get(booking=booking, kind=Kind.EARNING)
    assert earning.recorded_by_id == admin_user.id


def test_resolution_requires_a_note(complete_job, admin_user):
    booking = complete_job(final_price="2500", confirmed_price="2000")
    payment = Payment.objects.get(booking=booking)

    with pytest.raises(DomainError) as exc:
        services.resolve_flagged_payment(
            payment_id=payment.id, admin_user_id=admin_user.id,
            settled_amount=Decimal("2000"), note="",
        )
    assert exc.value.code == "note_required"


def test_settled_payment_cannot_be_resolved_again(complete_job, admin_user):
    booking = complete_job(final_price="2000")
    payment = Payment.objects.get(booking=booking)

    with pytest.raises(DomainError) as exc:
        services.resolve_flagged_payment(
            payment_id=payment.id, admin_user_id=admin_user.id,
            settled_amount=Decimal("1"), note="Trying to rewrite",
        )
    assert exc.value.code == "payment_not_flagged"


def test_payment_requires_a_completed_booking(customer, provider, service,
                                              dhanmondi):
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
        services.record_completion_payment(booking_id=booking.id)
    assert exc.value.code == "booking_not_complete"


def test_cancelled_booking_creates_no_payment(customer, provider, service,
                                              dhanmondi):
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
    booking_services.cancel_booking(
        booking_id=booking.id, actor=BookingEvent.Actor.CUSTOMER,
        actor_user_id=customer.user_id, reason="Plans changed",
        customer_id=customer.id,
    )
    assert not Payment.objects.filter(booking=booking).exists()


def test_auto_confirmed_booking_is_settled(customer, provider, service,
                                           dhanmondi,
                                           django_capture_on_commit_callbacks):
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
    booking_services.start_job(booking_id=booking.id,
                               provider_id=provider.id)
    booking_services.complete_job(booking_id=booking.id,
                                  provider_id=provider.id,
                                  final_price=Decimal("1500"))
    Booking.objects.filter(pk=booking.id).update(
        completed_at=timezone.now() - timezone.timedelta(hours=80),
    )

    with django_capture_on_commit_callbacks(execute=True):
        booking_services.auto_confirm_bookings()

    payment = Payment.objects.get(booking=booking)
    assert payment.status == Payment.Status.SETTLED
    assert payment.settled_amount == Decimal("1500.00")


def test_commission_rate_is_snapshotted(complete_job, settings):
    first = complete_job(final_price="1000")

    settings.PLATFORM_COMMISSION_PERCENT = 15
    second = complete_job(final_price="1000")

    first_payment = Payment.objects.get(booking=first)
    second_payment = Payment.objects.get(booking=second)
    assert first_payment.commission_amount == Decimal("120.00")
    assert second_payment.commission_amount == Decimal("150.00")


def test_settlement_reduces_the_payable(complete_job, provider, admin_user):
    complete_job(final_price="2000")

    services.record_provider_settlement(provider_id=provider.id,
                                        amount=Decimal("100"),
                                        admin_user_id=admin_user.id,
                                        reference="bKash TX123")
    assert services.outstanding_payable(provider.id) == Decimal("140.00")

    services.record_provider_settlement(provider_id=provider.id,
                                        amount=Decimal("140"),
                                        admin_user_id=admin_user.id)
    assert services.outstanding_payable(provider.id) == Decimal("0.00")
    assert services.balance_for(provider.id) == Decimal("0.00")


def test_settlement_cannot_exceed_the_payable(complete_job, provider,
                                              admin_user):
    complete_job(final_price="2000")

    with pytest.raises(DomainError) as exc:
        services.record_provider_settlement(provider_id=provider.id,
                                            amount=Decimal("240.01"),
                                            admin_user_id=admin_user.id)
    assert exc.value.code == "settlement_exceeds_payable"


def test_settlement_must_be_positive(provider, admin_user):
    with pytest.raises(DomainError) as exc:
        services.record_provider_settlement(provider_id=provider.id,
                                            amount=Decimal("0"),
                                            admin_user_id=admin_user.id)
    assert exc.value.code == "invalid_amount"


def test_earnings_summary_totals(complete_job, provider):
    complete_job(final_price="2000")
    complete_job(final_price="1500")

    summary = selectors.earnings_summary(provider.id)
    assert summary["gross"] == Decimal("3500.00")
    assert summary["commission"] == Decimal("420.00")
    assert summary["net"] == Decimal("3080.00")
    assert summary["jobs"] == 2
    assert summary["outstanding_payable"] == Decimal("420.00")


def test_earnings_summary_counts_flagged_payments(complete_job, provider):
    complete_job(final_price="2500", confirmed_price="2000")
    summary = selectors.earnings_summary(provider.id)
    assert summary["flagged_payments"] == 1
    assert summary["gross"] == Decimal("0.00")


def test_settlements_do_not_count_as_earnings(complete_job, provider,
                                              admin_user):
    complete_job(final_price="2000")
    services.record_provider_settlement(provider_id=provider.id,
                                        amount=Decimal("240"),
                                        admin_user_id=admin_user.id)

    summary = selectors.earnings_summary(provider.id)
    assert summary["gross"] == Decimal("2000.00")
    assert summary["commission"] == Decimal("240.00")


def test_earnings_grouped_by_period(complete_job, provider):
    complete_job(final_price="2000")
    complete_job(final_price="1500")

    rows = selectors.earnings_by_period(provider.id, period="month")
    assert len(rows) == 1
    assert rows[0]["gross"] == Decimal("3500.00")
    assert rows[0]["jobs"] == 2


def test_earnings_date_filter_excludes_other_ranges(complete_job, provider):
    complete_job(final_price="2000")
    tomorrow = timezone.localdate() + timezone.timedelta(days=1)

    summary = selectors.earnings_summary(provider.id, start=tomorrow)
    assert summary["gross"] == Decimal("0.00")
    assert summary["jobs"] == 0


def test_reconcile_clean_provider(complete_job, provider):
    complete_job(final_price="2000")
    complete_job(final_price="2500", confirmed_price="2000")
    assert services.reconcile_provider(provider.id) == []


def test_reconcile_detects_a_completed_booking_without_payment(
        customer, provider, service, dhanmondi):
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
    Booking.objects.filter(pk=booking.id).update(
        state=Booking.State.COMPLETED, final_price=Decimal("1800"),
        customer_confirmed_price=Decimal("1800"),
    )

    problems = services.reconcile_provider(provider.id)
    assert problems == [{"booking": booking.id, "issue": "missing_payment"}]

    assert services.backfill_missing_payments(provider.id) == 1
    assert services.reconcile_provider(provider.id) == []


def test_reconcile_detects_bulk_ledger_tampering(complete_job, provider):
    booking = complete_job(final_price="2000")
    LedgerEntry.objects.filter(booking=booking, kind=Kind.EARNING).update(
        amount=Decimal("9999"),
    )

    problems = services.reconcile_provider(provider.id)
    assert [p["issue"] for p in problems] == ["earning_mismatch"]
