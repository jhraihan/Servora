from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek

from .models import LedgerEntry, Payment, money

Kind = LedgerEntry.Kind

PERIOD_FUNCTIONS = {
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}

EARNING_SUM = Sum("amount", filter=Q(kind=Kind.EARNING))
COMMISSION_SUM = Sum("amount", filter=Q(kind=Kind.COMMISSION))
JOB_COUNT = Count("booking", filter=Q(kind=Kind.EARNING), distinct=True)


def _scoped_entries(provider_id, start=None, end=None):
    qs = LedgerEntry.objects.filter(provider_id=provider_id)
    if start is not None:
        qs = qs.filter(created_at__date__gte=start)
    if end is not None:
        qs = qs.filter(created_at__date__lte=end)
    return qs


def _shape(gross, commission, jobs):
    gross = money(gross or 0)
    commission = money(-(commission or 0))
    return {
        "gross": gross,
        "commission": commission,
        "net": money(gross - commission),
        "jobs": jobs or 0,
    }


def earnings_summary(provider_id, *, start=None, end=None):
    totals = _scoped_entries(provider_id, start, end).aggregate(
        gross=EARNING_SUM, commission=COMMISSION_SUM, jobs=JOB_COUNT,
    )
    summary = _shape(totals["gross"], totals["commission"], totals["jobs"])

    balance = money(
        LedgerEntry.objects.filter(provider_id=provider_id)
        .aggregate(total=Sum("amount"))["total"] or 0
    )
    summary["balance"] = balance
    summary["outstanding_payable"] = money(-balance) if balance < 0 \
        else money(0)
    summary["outstanding_receivable"] = balance if balance > 0 \
        else money(0)
    summary["flagged_payments"] = Payment.objects.filter(
        provider_id=provider_id, status=Payment.Status.FLAGGED,
    ).count()
    return summary


def earnings_by_period(provider_id, *, period="month", start=None,
                       end=None):
    trunc = PERIOD_FUNCTIONS.get(period, TruncMonth)
    rows = (
        _scoped_entries(provider_id, start, end)
        .annotate(bucket=trunc("created_at"))
        .values("bucket")
        .annotate(gross=EARNING_SUM, commission=COMMISSION_SUM,
                  jobs=JOB_COUNT)
        .order_by("-bucket")
    )
    return [
        {"period": row["bucket"].date().isoformat(),
         **_shape(row["gross"], row["commission"], row["jobs"])}
        for row in rows
        if row["gross"] or row["commission"]
    ]


def ledger_for(provider_id, *, kind=None):
    qs = (
        LedgerEntry.objects
        .filter(provider_id=provider_id)
        .select_related("booking")
    )
    if kind:
        qs = qs.filter(kind=kind)
    return qs


def payments_for(*, customer_id=None, provider_id=None):
    qs = Payment.objects.select_related("booking", "provider")
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    if provider_id is not None:
        qs = qs.filter(provider_id=provider_id)
    return qs


def flagged_payments():
    return (
        Payment.objects
        .filter(status=Payment.Status.FLAGGED)
        .select_related("booking", "provider", "customer",
                        "customer__user")
        .order_by("flagged_at")
    )
