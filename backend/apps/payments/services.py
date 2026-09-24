import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import ProviderProfile
from apps.bookings.models import Booking
from apps.common.exceptions import DomainError, NotFound

from .models import LedgerEntry, Payment, commission_for, money

logger = logging.getLogger(__name__)

Kind = LedgerEntry.Kind


def current_commission_rate():
    return Decimal(str(settings.PLATFORM_COMMISSION_PERCENT))


@transaction.atomic
def record_completion_payment(*, booking_id):
    booking = (
        Booking.objects
        .select_for_update()
        .filter(pk=booking_id)
        .first()
    )
    if booking is None:
        raise NotFound("No such booking.", code="booking_not_found")

    if booking.state != Booking.State.COMPLETED:
        raise DomainError(
            "Payment is recorded only for a completed booking.",
            code="booking_not_complete",
            details={"state": booking.state},
        )

    existing = Payment.objects.filter(
        booking=booking, method=Payment.Method.CASH,
    ).first()
    if existing is not None:
        return existing

    recorded = money(booking.final_price
                     if booking.final_price is not None
                     else booking.agreed_price)
    confirmed = money(booking.customer_confirmed_price
                      if booking.customer_confirmed_price is not None
                      else recorded)

    payment = Payment.objects.create(
        booking=booking,
        provider_id=booking.provider_id,
        customer_id=booking.customer_id,
        method=Payment.Method.CASH,
        provider_recorded_amount=recorded,
        customer_confirmed_amount=confirmed,
        commission_rate=current_commission_rate(),
    )

    if recorded != confirmed:
        payment.status = Payment.Status.FLAGGED
        payment.flagged_at = timezone.now()
        payment.save(update_fields=["status", "flagged_at", "updated_at"])
        logger.warning(
            "Payment %s flagged: provider recorded %s, customer confirmed %s",
            payment.id, recorded, confirmed,
        )
        return payment

    return _settle(payment, recorded)


def _settle(payment, amount, *, recorded_by_id=None):
    amount = money(amount)
    commission = commission_for(amount, payment.commission_rate)

    payment.status = Payment.Status.SETTLED
    payment.settled_amount = amount
    payment.commission_amount = commission
    payment.settled_at = timezone.now()
    payment.save(update_fields=["status", "settled_amount",
                                "commission_amount", "settled_at",
                                "updated_at"])

    shared = {
        "provider_id": payment.provider_id,
        "booking_id": payment.booking_id,
        "payment": payment,
        "recorded_by_id": recorded_by_id,
    }
    LedgerEntry.objects.create(
        kind=Kind.EARNING, amount=amount,
        description="Job #%s completed" % payment.booking_id, **shared,
    )
    LedgerEntry.objects.create(
        kind=Kind.COMMISSION, amount=-commission,
        description="%s%% platform commission" % payment.commission_rate,
        **shared,
    )
    if payment.method == Payment.Method.CASH:
        LedgerEntry.objects.create(
            kind=Kind.CASH_RETAINED, amount=-amount,
            description="Cash collected directly from the customer",
            **shared,
        )

    logger.info("Payment %s settled at %s, commission %s",
                payment.id, amount, commission)
    return payment


@transaction.atomic
def resolve_flagged_payment(*, payment_id, admin_user_id, settled_amount,
                            note):
    payment = (
        Payment.objects
        .select_for_update()
        .filter(pk=payment_id)
        .first()
    )
    if payment is None:
        raise NotFound("No such payment.", code="payment_not_found")

    if payment.status != Payment.Status.FLAGGED:
        raise DomainError(
            "Only a flagged payment can be resolved.",
            code="payment_not_flagged",
            details={"status": payment.status},
        )

    if not note:
        raise DomainError("A resolution needs a note.",
                          code="note_required")

    if settled_amount is None or settled_amount < 0:
        raise DomainError("Settled amount must be zero or more.",
                          code="invalid_amount")

    payment.resolved_by_id = admin_user_id
    payment.resolution_note = note
    payment.save(update_fields=["resolved_by", "resolution_note",
                                "updated_at"])
    return _settle(payment, settled_amount, recorded_by_id=admin_user_id)


def balance_for(provider_id):
    total = (
        LedgerEntry.objects
        .filter(provider_id=provider_id)
        .aggregate(total=Sum("amount"))["total"]
    )
    return money(total or 0)


def outstanding_payable(provider_id):
    balance = balance_for(provider_id)
    return money(-balance) if balance < 0 else money(0)


@transaction.atomic
def record_provider_settlement(*, provider_id, amount, admin_user_id,
                               reference=""):
    provider = (
        ProviderProfile.objects
        .select_for_update()
        .filter(pk=provider_id)
        .first()
    )
    if provider is None:
        raise NotFound("No such provider.", code="provider_not_found")

    amount = money(amount)
    if amount <= 0:
        raise DomainError("A settlement must be a positive amount.",
                          code="invalid_amount")

    owed = outstanding_payable(provider_id)
    if amount > owed:
        raise DomainError(
            "Settlement exceeds the outstanding payable.",
            code="settlement_exceeds_payable",
            details={"outstanding_payable": str(owed)},
        )

    entry = LedgerEntry.objects.create(
        provider=provider,
        kind=Kind.SETTLEMENT,
        amount=amount,
        description="Commission settled with the platform",
        recorded_by_id=admin_user_id,
        reference=reference,
    )
    logger.info("Provider %s settled %s", provider_id, amount)
    return entry


def reconcile_provider(provider_id):
    problems = []

    completed = Booking.objects.filter(
        provider_id=provider_id, state=Booking.State.COMPLETED,
    )
    payments = {
        p.booking_id: p for p in Payment.objects.filter(
            provider_id=provider_id, method=Payment.Method.CASH,
        )
    }

    for booking in completed:
        if booking.pk not in payments:
            problems.append({"booking": booking.pk,
                             "issue": "missing_payment"})

    entries = {}
    for entry in LedgerEntry.objects.filter(
        provider_id=provider_id, kind__in=LedgerEntry.PER_BOOKING_KINDS,
    ):
        entries[(entry.booking_id, entry.kind)] = entry.amount

    for booking_id, payment in payments.items():
        earning = entries.get((booking_id, Kind.EARNING))
        commission = entries.get((booking_id, Kind.COMMISSION))

        if payment.status == Payment.Status.SETTLED:
            if earning != payment.settled_amount:
                problems.append({"booking": booking_id,
                                 "issue": "earning_mismatch",
                                 "ledger": str(earning),
                                 "payment": str(payment.settled_amount)})
            if commission is None or -commission != payment.commission_amount:
                problems.append({"booking": booking_id,
                                 "issue": "commission_mismatch",
                                 "ledger": str(commission),
                                 "payment": str(payment.commission_amount)})
        elif earning is not None or commission is not None:
            problems.append({"booking": booking_id,
                             "issue": "unsettled_payment_in_ledger",
                             "status": payment.status})

    return problems


def backfill_missing_payments(provider_id=None):
    qs = Booking.objects.filter(state=Booking.State.COMPLETED).exclude(
        pk__in=Payment.objects.filter(
            method=Payment.Method.CASH,
        ).values("booking_id"),
    )
    if provider_id is not None:
        qs = qs.filter(provider_id=provider_id)

    created = 0
    for booking_id in qs.values_list("pk", flat=True):
        record_completion_payment(booking_id=booking_id)
        created += 1
    return created
