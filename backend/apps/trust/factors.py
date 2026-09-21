from dataclasses import dataclass, field
from math import log

ALGO_VERSION = "v1.0"

WEIGHTS = {
    "f1_verification": 0.20,
    "f2_volume": 0.15,
    "f3_completion": 0.20,
    "f4_cancellation": 0.15,
    "f5_response": 0.10,
    "f6_reviews": 0.20,
}

VOLUME_SATURATION = 100
COMPLETION_PRIOR_MU = 0.90
COMPLETION_PRIOR_K = 10
REVIEW_PRIOR_MU = 4.2
REVIEW_PRIOR_K = 5
CANCEL_EXPONENT = 1.5
CANCEL_HALF_LIFE_DAYS = 180
REVIEW_HALF_LIFE_DAYS = 365

MIN_RESPONSES_FOR_F5 = 5
NEUTRAL_F5 = 60.0
UNANSWERED_RESPONSE_SECONDS = 24 * 3600

VERIFICATION_POINTS = {
    "phone_verified": 30,
    "identity_verified": 40,
    "skill_verified": 20,
    "address_verified": 10,
}

PENALTY_DISPUTE_RECENT = 15
PENALTY_DISPUTE_REPEATED = 25
PENALTY_NO_SHOW_RECENT = 10
PENALTY_UNDER_INVESTIGATION = 20


@dataclass
class TrustInputs:
    phone_verified: bool = False
    identity_verified: bool = False
    skill_verified: bool = False
    address_verified: bool = False

    jobs_completed: int = 0
    jobs_accepted: int = 0

    cancellations: list = field(default_factory=list)

    median_response_seconds: int = None
    response_count: int = 0

    reviews: list = field(default_factory=list)

    upheld_disputes_90d: int = 0
    upheld_disputes_180d: int = 0
    no_shows_30d: int = 0
    under_investigation: bool = False


def decay(days_ago, half_life):
    return 0.5 ** (days_ago / float(half_life))


def cancellation_weight(notice_hours, no_show=False):
    if no_show:
        return 6.0
    if notice_hours >= 24:
        return 1.0
    if notice_hours >= 4:
        return 2.0
    return 4.0


def f1_verification(inputs):
    score = sum(
        points for flag, points in VERIFICATION_POINTS.items()
        if getattr(inputs, flag)
    )
    return float(min(score, 100))


def f2_volume(inputs):
    completed = inputs.jobs_completed
    if completed <= 0:
        return 0.0
    raw = 100.0 * log(1 + completed) / log(1 + VOLUME_SATURATION)
    return min(raw, 100.0)


def f3_completion(inputs):
    k, mu = COMPLETION_PRIOR_K, COMPLETION_PRIOR_MU
    return 100.0 * (inputs.jobs_completed + k * mu) / (inputs.jobs_accepted + k)


def f4_cancellation(inputs):
    if inputs.jobs_accepted <= 0:
        return 100.0

    weighted = sum(
        cancellation_weight(notice_hours, no_show)
        * decay(days_ago, CANCEL_HALF_LIFE_DAYS)
        for notice_hours, days_ago, no_show in inputs.cancellations
    )
    rate = weighted / float(inputs.jobs_accepted)
    return 100.0 * (1 - min(rate, 1.0)) ** CANCEL_EXPONENT


def f5_response(inputs):
    if inputs.response_count < MIN_RESPONSES_FOR_F5:
        return NEUTRAL_F5
    if inputs.median_response_seconds is None:
        return NEUTRAL_F5

    minutes = inputs.median_response_seconds / 60.0
    if minutes <= 5:
        return 100.0
    if minutes <= 60:
        return 100 - 30 * (minutes - 5) / 55.0
    if minutes <= 240:
        return 70 - 30 * (minutes - 60) / 180.0
    if minutes <= 1440:
        return 40 - 40 * (minutes - 240) / 1200.0
    return 0.0


def f6_reviews(inputs):
    weighted_sum = sum(
        rating * decay(days_ago, REVIEW_HALF_LIFE_DAYS)
        for rating, days_ago in inputs.reviews
    )
    weighted_count = sum(
        decay(days_ago, REVIEW_HALF_LIFE_DAYS)
        for _rating, days_ago in inputs.reviews
    )
    k, mu = REVIEW_PRIOR_K, REVIEW_PRIOR_MU
    bayes = (weighted_sum + k * mu) / (weighted_count + k)
    return 100.0 * (bayes - 1) / 4.0


FACTOR_FUNCTIONS = {
    "f1_verification": f1_verification,
    "f2_volume": f2_volume,
    "f3_completion": f3_completion,
    "f4_cancellation": f4_cancellation,
    "f5_response": f5_response,
    "f6_reviews": f6_reviews,
}


def compute_factors(inputs):
    return {name: fn(inputs) for name, fn in FACTOR_FUNCTIONS.items()}


def compute_penalties(inputs):
    penalty = 0
    if inputs.upheld_disputes_90d >= 1:
        penalty += PENALTY_DISPUTE_RECENT
    if inputs.upheld_disputes_180d >= 2:
        penalty += PENALTY_DISPUTE_REPEATED
    if inputs.no_shows_30d >= 1:
        penalty += PENALTY_NO_SHOW_RECENT
    if inputs.under_investigation:
        penalty += PENALTY_UNDER_INVESTIGATION
    return penalty


def compose(factors, penalties=0):
    base = sum(factors[name] * weight for name, weight in WEIGHTS.items())
    total = max(0.0, min(100.0, base - penalties))
    return base, total


def score(inputs):
    factors = compute_factors(inputs)
    penalties = compute_penalties(inputs)
    base, total = compose(factors, penalties)
    return {
        "factors": factors,
        "weights": dict(WEIGHTS),
        "weighted": {
            name: factors[name] * weight for name, weight in WEIGHTS.items()
        },
        "base": base,
        "penalties": penalties,
        "total": total,
        "algo_version": ALGO_VERSION,
    }
