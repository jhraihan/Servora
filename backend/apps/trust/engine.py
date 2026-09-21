import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ProviderProfile
from apps.common.exceptions import NotFound

from . import factors
from .factors import TrustInputs
from .models import TrustSnapshot

logger = logging.getLogger(__name__)

TIER_NEW_MAX_JOBS = 3
TIER_RISING_MIN_SCORE = 55
TIER_ESTABLISHED_MIN_SCORE = 70
TIER_ESTABLISHED_MIN_JOBS = 10
TIER_TRUSTED_MIN_SCORE = 85
TIER_TRUSTED_MIN_JOBS = 25

REVIEW_FLAG_MAX_SCORE = 40
REVIEW_FLAG_MIN_JOBS = 10


def gather_inputs(provider):
    return TrustInputs(
        phone_verified=provider.user.phone_verified,
        identity_verified=provider.identity_verified,
        skill_verified=provider.skill_verified,
        address_verified=provider.address_verified,

        jobs_completed=provider.jobs_completed,
        jobs_accepted=provider.jobs_accepted,

        cancellations=_gather_cancellations(provider),

        median_response_seconds=provider.median_response_seconds,
        response_count=provider.requests_received,

        reviews=_gather_reviews(provider),

        upheld_disputes_90d=_count_upheld_disputes(provider, days=90),
        upheld_disputes_180d=_count_upheld_disputes(provider, days=180),
        no_shows_30d=_count_no_shows(provider, days=30),
        under_investigation=provider.trust_tier == ProviderProfile.Tier.UNDER_REVIEW,
    )


def _gather_cancellations(provider):
    bookings = getattr(provider, "bookings", None)
    if bookings is None:
        return [(48, 0, False)] * provider.jobs_cancelled

    records = []
    now = timezone.now()
    for booking in bookings.filter(
        state__in=["cancelled_provider", "expired"]
    ).only("scheduled_for", "cancelled_at", "cancelled_by"):
        cancelled_at = getattr(booking, "cancelled_at", None) or now
        notice_hours = max(
            (booking.scheduled_for - cancelled_at).total_seconds() / 3600.0, 0
        )
        days_ago = max((now - cancelled_at).days, 0)
        no_show = getattr(booking, "was_no_show", False)
        records.append((notice_hours, days_ago, no_show))
    return records


def _gather_reviews(provider):
    reviews = getattr(provider, "reviews", None)
    if reviews is None:
        return []

    now = timezone.now()
    return [
        (float(review.rating), max((now - review.created_at).days, 0))
        for review in reviews.filter(is_hidden=False).only(
            "rating", "created_at"
        )
    ]


def _count_upheld_disputes(provider, days):
    disputes = getattr(provider, "disputes", None)
    if disputes is None:
        return 0
    cutoff = timezone.now() - timezone.timedelta(days=days)
    return disputes.filter(upheld=True, resolved_at__gte=cutoff).count()


def _count_no_shows(provider, days):
    bookings = getattr(provider, "bookings", None)
    if bookings is None:
        return 0
    cutoff = timezone.now() - timezone.timedelta(days=days)
    return bookings.filter(was_no_show=True,
                           scheduled_for__gte=cutoff).count()


def resolve_tier(score, *, jobs_completed, identity_verified,
                 under_investigation=False):
    if under_investigation:
        return ProviderProfile.Tier.UNDER_REVIEW

    if jobs_completed < TIER_NEW_MAX_JOBS:
        return ProviderProfile.Tier.NEW

    if (score >= TIER_TRUSTED_MIN_SCORE
            and jobs_completed >= TIER_TRUSTED_MIN_JOBS
            and identity_verified):
        return ProviderProfile.Tier.TRUSTED_PRO

    if (score >= TIER_ESTABLISHED_MIN_SCORE
            and jobs_completed >= TIER_ESTABLISHED_MIN_JOBS
            and identity_verified):
        return ProviderProfile.Tier.ESTABLISHED

    if score >= TIER_RISING_MIN_SCORE:
        return ProviderProfile.Tier.RISING

    return ProviderProfile.Tier.RISING


def needs_admin_review(score, jobs_completed):
    return (score < REVIEW_FLAG_MAX_SCORE
            and jobs_completed >= REVIEW_FLAG_MIN_JOBS)


def evaluate(provider):
    inputs = gather_inputs(provider)
    result = factors.score(inputs)

    result["tier"] = resolve_tier(
        result["total"],
        jobs_completed=provider.jobs_completed,
        identity_verified=provider.identity_verified,
        under_investigation=inputs.under_investigation,
    )
    result["needs_admin_review"] = needs_admin_review(
        result["total"], provider.jobs_completed,
    )
    return result


@transaction.atomic
def recompute(provider_id, *, trigger=TrustSnapshot.Trigger.MANUAL):
    provider = (
        ProviderProfile.objects
        .select_for_update()
        .select_related("user")
        .filter(pk=provider_id)
        .first()
    )
    if provider is None:
        raise NotFound("No such provider.", code="provider_not_found")

    result = evaluate(provider)
    score = Decimal("%.2f" % result["total"])

    snapshot = TrustSnapshot.objects.create(
        provider=provider,
        score=score,
        tier=result["tier"],
        factors=_snapshot_payload(result),
        algo_version=result["algo_version"],
        trigger=trigger,
    )

    provider.trust_score = score
    provider.trust_tier = result["tier"]
    provider.trust_computed_at = timezone.now()
    provider.save(update_fields=[
        "trust_score", "trust_tier", "trust_computed_at", "updated_at",
    ])

    logger.info("Trust recomputed for provider %s: %s (%s) via %s",
                provider_id, score, result["tier"], trigger)
    return snapshot


def _snapshot_payload(result):
    return {
        "factors": {k: round(v, 4) for k, v in result["factors"].items()},
        "weights": result["weights"],
        "weighted": {k: round(v, 4) for k, v in result["weighted"].items()},
        "base": round(result["base"], 4),
        "penalties": result["penalties"],
        "total": round(result["total"], 4),
        "tier": result["tier"],
        "needs_admin_review": result["needs_admin_review"],
    }


def recompute_all(*, trigger=TrustSnapshot.Trigger.NIGHTLY_BATCH,
                  only_active=True):
    queryset = ProviderProfile.objects.select_related("user")
    if only_active:
        queryset = queryset.filter(user__is_active=True)

    count = 0
    for provider_id in queryset.values_list("pk", flat=True).iterator():
        recompute(provider_id, trigger=trigger)
        count += 1
    return count


def breakdown(provider):
    result = evaluate(provider)
    return {
        "score": round(result["total"], 2),
        "tier": result["tier"],
        "algo_version": result["algo_version"],
        "verification": {
            "phone_verified": provider.user.phone_verified,
            "identity_verified": provider.identity_verified,
            "skill_verified": provider.skill_verified,
            "address_verified": provider.address_verified,
        },
        "evidence": {
            "jobs_completed": provider.jobs_completed,
            "jobs_accepted": provider.jobs_accepted,
            "jobs_cancelled": provider.jobs_cancelled,
            "completion_rate": _rate(provider.jobs_completed,
                                     provider.jobs_accepted),
            "cancellation_rate": _rate(provider.jobs_cancelled,
                                       provider.jobs_accepted),
            "median_response_seconds": provider.median_response_seconds,
        },
        "factors": [
            {
                "key": key,
                "label": label,
                "score": round(result["factors"][key], 1),
                "weight": result["weights"][key],
                "contribution": round(result["weighted"][key], 2),
            }
            for key, label in FACTOR_LABELS
        ],
        "penalties": result["penalties"],
        "computed_at": provider.trust_computed_at,
    }


FACTOR_LABELS = [
    ("f1_verification", "Verification depth"),
    ("f2_volume", "Job volume"),
    ("f3_completion", "Completion reliability"),
    ("f4_cancellation", "Cancellation discipline"),
    ("f5_response", "Responsiveness"),
    ("f6_reviews", "Review quality"),
]


def _rate(numerator, denominator):
    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 1)
