# -*- coding: utf-8 -*-
"""
Reference implementation of the PRD section 7 trust algorithm, plus assertions
that reproduce the two worked examples in section 7.4.

    python docs/verify_trust_math.py

This exists so the numbers printed in the PRD can be re-checked whenever the
weights or formulas are tuned. It is also the starting point for
apps/trust/factors.py -- the production code should produce identical output.
"""

from math import log

ALGO_VERSION = "v1.0"

WEIGHTS = {
    "f1_verification": 0.20,
    "f2_volume":       0.15,
    "f3_completion":   0.20,
    "f4_cancellation": 0.15,
    "f5_response":     0.10,
    "f6_reviews":      0.20,
}

VOLUME_SATURATION = 100      # jobs at which F2 reaches 100
COMPLETION_PRIOR_MU = 0.90   # platform prior completion rate
COMPLETION_PRIOR_K = 10      # prior strength in pseudo-jobs
REVIEW_PRIOR_MU = 4.2        # platform prior mean rating
REVIEW_PRIOR_K = 5           # prior strength in pseudo-reviews
CANCEL_EXPONENT = 1.5
CANCEL_HALF_LIFE_DAYS = 180
REVIEW_HALF_LIFE_DAYS = 365


# ---------------------------------------------------------------- factors
def f1_verification(phone=False, identity=False, skill=False, address=False):
    """Step function over admin-confirmed facts. Capped at 100."""
    score = 0
    if phone:
        score += 30
    if identity:
        score += 40
    if skill:
        score += 20
    if address:
        score += 10
    return float(min(score, 100))


def f2_volume(completed):
    """Logarithmic, saturating at VOLUME_SATURATION jobs."""
    if completed <= 0:
        return 0.0
    raw = 100.0 * log(1 + completed) / log(1 + VOLUME_SATURATION)
    return min(raw, 100.0)


def f3_completion(completed, accepted):
    """Bayesian-smoothed completion rate, so low volume cannot score 100."""
    k, mu = COMPLETION_PRIOR_K, COMPLETION_PRIOR_MU
    return 100.0 * (completed + k * mu) / (accepted + k)


def cancel_weight(notice_hours, no_show=False):
    """Damage weight for one cancellation, by notice given."""
    if no_show:
        return 6.0
    if notice_hours >= 24:
        return 1.0
    if notice_hours >= 4:
        return 2.0
    return 4.0


def decay(days_ago, half_life):
    return 0.5 ** (days_ago / float(half_life))


def f4_cancellation(cancellations, accepted):
    """
    cancellations: list of (notice_hours, days_ago, no_show)
    Superlinear penalty on the time-decayed, damage-weighted rate.
    """
    if accepted <= 0:
        return 100.0
    weighted = sum(
        cancel_weight(notice, no_show) * decay(days_ago, CANCEL_HALF_LIFE_DAYS)
        for notice, days_ago, no_show in cancellations
    )
    rate = weighted / float(accepted)
    return 100.0 * (1 - min(rate, 1.0)) ** CANCEL_EXPONENT


def f5_response(median_seconds, response_count):
    """Piecewise-linear decay over median response time."""
    if response_count < 5:
        return 60.0                      # neutral: not enough evidence
    t = median_seconds / 60.0            # minutes
    if t <= 5:
        return 100.0
    if t <= 60:
        return 100 - 30 * (t - 5) / 55.0
    if t <= 240:
        return 70 - 30 * (t - 60) / 180.0
    if t <= 1440:
        return 40 - 40 * (t - 240) / 1200.0
    return 0.0


def f6_reviews(reviews):
    """
    reviews: list of (rating, days_ago)
    Recency-weighted then Bayesian-smoothed, mapped from 1-5 onto 0-100.
    """
    wsum = sum(r * decay(d, REVIEW_HALF_LIFE_DAYS) for r, d in reviews)
    wcount = sum(decay(d, REVIEW_HALF_LIFE_DAYS) for r, d in reviews)
    k, mu = REVIEW_PRIOR_K, REVIEW_PRIOR_MU
    bayes = (wsum + k * mu) / (wcount + k)
    return 100.0 * (bayes - 1) / 4.0


# ------------------------------------------------------------- composition
def compose(factors, penalties=0):
    base = sum(factors[name] * w for name, w in WEIGHTS.items())
    return base, max(0.0, min(100.0, base - penalties))


def tier(score, completed, identity_verified):
    if completed < 3:
        return "New"
    if score >= 85 and completed >= 25 and identity_verified:
        return "Trusted Pro"
    if score >= 70 and completed >= 10 and identity_verified:
        return "Established"
    if score >= 55:
        return "Rising"
    return "Rising"


def report(name, factors, base, total, tier_name):
    print("\n%s" % name)
    print("-" * 52)
    for key, w in WEIGHTS.items():
        v = factors[key]
        print("  %-18s %6.1f  x %.2f  = %6.2f" % (key, v, w, v * w))
    print("  %-18s %25s%6.2f" % ("base", "", base))
    print("  %-18s %25s%6.2f  -> %s" % ("TRUST", "", total, tier_name))


# ------------------------------------------------------------------- tests
def example_kamal():
    """Experienced provider, fully verified, only 4 jobs on-platform."""
    factors = {
        "f1_verification": f1_verification(phone=True, identity=True,
                                           skill=True),
        "f2_volume":       f2_volume(4),
        "f3_completion":   f3_completion(4, 4),
        "f4_cancellation": f4_cancellation([], accepted=4),
        "f5_response":     f5_response(8 * 60, response_count=6),
        "f6_reviews":      f6_reviews([(4.9, 10)] * 4),
    }
    # PRD table uses undecayed reviews for legibility
    factors["f6_reviews"] = f6_reviews([(4.9, 0)] * 4)
    base, total = compose(factors, penalties=0)
    return factors, base, total


def example_shakib():
    """High star rating, poor reliability -- the provider ratings hide."""
    cancels = ([(2, 0, False)] * 3) + ([(48, 0, False)] * 9)
    factors = {
        "f1_verification": f1_verification(phone=True),
        "f2_volume":       f2_volume(18),
        "f3_completion":   f3_completion(18, 30),
        "f4_cancellation": f4_cancellation(cancels, accepted=30),
        "f5_response":     f5_response(6 * 3600, response_count=30),
        "f6_reviews":      f6_reviews([(4.8, 0)] * 18),
    }
    base, total = compose(factors, penalties=0)
    return factors, base, total


def main():
    kf, kb, kt = example_kamal()
    report("Kamal -- experienced, newly joined", kf, kb, kt,
           tier(kt, 4, True))

    sf, sb, st = example_shakib()
    report("Shakib -- high rating, poor reliability", sf, sb, st,
           tier(st, 18, False))

    # assertions: these must match the PRD section 7.4 tables
    checks = [
        ("kamal f3", kf["f3_completion"], 92.9),
        ("kamal f6", kf["f6_reviews"],    87.8),
        ("kamal base", kb,                84.19),
        ("shakib f4", sf["f4_cancellation"], 16.4),
        ("shakib f5", sf["f5_response"],     36.0),
        ("shakib f6", sf["f6_reviews"],      91.7),
        ("shakib base", sb,                  53.48),
    ]
    print("\nPRD table checks")
    print("-" * 52)
    failed = 0
    for label, got, want in checks:
        ok = abs(got - want) < 0.05
        failed += 0 if ok else 1
        print("  %-14s got %7.2f  want %7.2f  %s"
              % (label, got, want, "OK" if ok else "MISMATCH"))

    print()
    if failed:
        raise SystemExit("%d check(s) failed" % failed)
    print("All PRD section 7.4 figures reproduce exactly.")


if __name__ == "__main__":
    main()
