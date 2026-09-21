import pytest

from apps.trust import factors
from apps.trust.factors import TrustInputs


def test_weights_sum_to_one():
    assert abs(sum(factors.WEIGHTS.values()) - 1.0) < 1e-9


@pytest.mark.parametrize("flags,expected", [
    ({}, 0),
    ({"phone_verified": True}, 30),
    ({"phone_verified": True, "identity_verified": True}, 70),
    ({"phone_verified": True, "identity_verified": True,
      "skill_verified": True}, 90),
    ({"phone_verified": True, "identity_verified": True,
      "skill_verified": True, "address_verified": True}, 100),
])
def test_f1_step_function(flags, expected):
    assert factors.f1_verification(TrustInputs(**flags)) == expected


@pytest.mark.parametrize("completed,expected", [
    (0, 0.0),
    (5, 38.9),
    (25, 70.6),
    (100, 100.0),
    (300, 100.0),
])
def test_f2_logarithmic_saturation(completed, expected):
    got = factors.f2_volume(TrustInputs(jobs_completed=completed))
    assert abs(got - expected) < 0.1


def test_f2_never_exceeds_100():
    assert factors.f2_volume(TrustInputs(jobs_completed=100_000)) == 100.0


@pytest.mark.parametrize("completed,accepted,expected", [
    (1, 1, 90.9),
    (0, 1, 81.8),
    (189, 200, 94.3),
    (5, 20, 46.7),
])
def test_f3_bayesian_smoothing(completed, accepted, expected):
    got = factors.f3_completion(
        TrustInputs(jobs_completed=completed, jobs_accepted=accepted)
    )
    assert abs(got - expected) < 0.1


def test_f3_single_perfect_job_scores_below_long_record():
    rookie = factors.f3_completion(
        TrustInputs(jobs_completed=1, jobs_accepted=1)
    )
    veteran = factors.f3_completion(
        TrustInputs(jobs_completed=189, jobs_accepted=200)
    )
    assert rookie < veteran


def test_f4_no_cancellations_is_perfect():
    assert factors.f4_cancellation(
        TrustInputs(jobs_accepted=10)
    ) == 100.0


def test_f4_weights_late_cancellations_more_heavily():
    early = factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(48, 0, False)],
    ))
    late = factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(1, 0, False)],
    ))
    no_show = factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(0, 0, True)],
    ))
    assert early > late > no_show


def test_f4_decays_with_age():
    recent = factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(1, 0, False)],
    ))
    old = factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(1, 360, False)],
    ))
    assert old > recent


def test_f4_matches_prd_penalty_curve():
    mild = 100 - factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(48, 0, False)],
    ))
    heavy = 100 - factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(48, 0, False)] * 3,
    ))
    assert abs(mild - 15) < 1.0
    assert abs(heavy - 41) < 1.0


def test_f4_penalty_grows_monotonically_with_rate():
    penalties = [
        100 - factors.f4_cancellation(TrustInputs(
            jobs_accepted=10, cancellations=[(48, 0, False)] * n,
        ))
        for n in range(1, 8)
    ]
    assert penalties == sorted(penalties)


def test_f4_first_cancellation_costs_more_than_a_linear_share():
    one = 100 - factors.f4_cancellation(TrustInputs(
        jobs_accepted=10, cancellations=[(48, 0, False)],
    ))
    assert one > 10.0


def test_f4_clamps_at_zero():
    assert factors.f4_cancellation(TrustInputs(
        jobs_accepted=2, cancellations=[(0, 0, True)] * 5,
    )) == 0.0


@pytest.mark.parametrize("seconds,expected", [
    (60, 100.0),
    (5 * 60, 100.0),
    (8 * 60, 98.4),
    (60 * 60, 70.0),
    (4 * 3600, 40.0),
    (6 * 3600, 36.0),
    (24 * 3600, 0.0),
    (48 * 3600, 0.0),
])
def test_f5_piecewise_decay(seconds, expected):
    got = factors.f5_response(
        TrustInputs(median_response_seconds=seconds, response_count=30)
    )
    assert abs(got - expected) < 0.1


def test_f5_neutral_below_minimum_sample():
    assert factors.f5_response(
        TrustInputs(median_response_seconds=60, response_count=4)
    ) == factors.NEUTRAL_F5


def test_f5_neutral_when_no_measurement():
    assert factors.f5_response(
        TrustInputs(median_response_seconds=None, response_count=30)
    ) == factors.NEUTRAL_F5


def test_f6_no_reviews_returns_prior():
    got = factors.f6_reviews(TrustInputs(reviews=[]))
    expected = 100.0 * (factors.REVIEW_PRIOR_MU - 1) / 4.0
    assert abs(got - expected) < 0.01


def test_f6_single_five_star_does_not_reach_100():
    assert factors.f6_reviews(TrustInputs(reviews=[(5.0, 0)])) < 100.0


def test_f6_recency_weighting():
    fresh = factors.f6_reviews(TrustInputs(reviews=[(5.0, 0)] * 10))
    stale = factors.f6_reviews(TrustInputs(reviews=[(5.0, 730)] * 10))
    assert fresh > stale


def test_f6_maps_one_star_to_zero():
    got = factors.f6_reviews(TrustInputs(reviews=[(1.0, 0)] * 200))
    assert got < 5.0


def test_penalties_accumulate():
    inputs = TrustInputs(
        upheld_disputes_90d=1, upheld_disputes_180d=2,
        no_shows_30d=1, under_investigation=True,
    )
    assert factors.compute_penalties(inputs) == (
        factors.PENALTY_DISPUTE_RECENT
        + factors.PENALTY_DISPUTE_REPEATED
        + factors.PENALTY_NO_SHOW_RECENT
        + factors.PENALTY_UNDER_INVESTIGATION
    )


def test_penalties_applied_after_weighting():
    clean = TrustInputs(
        phone_verified=True, identity_verified=True, skill_verified=True,
        jobs_completed=50, jobs_accepted=50, reviews=[(5.0, 0)] * 50,
        median_response_seconds=120, response_count=50,
    )
    penalised = TrustInputs(**{**clean.__dict__, "under_investigation": True})

    clean_result = factors.score(clean)
    penalised_result = factors.score(penalised)

    assert clean_result["base"] == penalised_result["base"]
    assert (clean_result["total"] - penalised_result["total"]) == \
        factors.PENALTY_UNDER_INVESTIGATION


def test_score_clamped_to_range():
    worst = TrustInputs(
        jobs_accepted=10, cancellations=[(0, 0, True)] * 20,
        reviews=[(1.0, 0)] * 50, median_response_seconds=48 * 3600,
        response_count=50, upheld_disputes_90d=3, upheld_disputes_180d=5,
        no_shows_30d=3, under_investigation=True,
    )
    assert 0.0 <= factors.score(worst)["total"] <= 100.0


def test_kamal_reproduces_prd_worked_example():
    kamal = TrustInputs(
        phone_verified=True, identity_verified=True, skill_verified=True,
        jobs_completed=4, jobs_accepted=4,
        cancellations=[],
        median_response_seconds=8 * 60, response_count=6,
        reviews=[(4.9, 0)] * 4,
    )
    result = factors.score(kamal)

    assert abs(result["factors"]["f1_verification"] - 90.0) < 0.05
    assert abs(result["factors"]["f2_volume"] - 34.9) < 0.05
    assert abs(result["factors"]["f3_completion"] - 92.9) < 0.05
    assert abs(result["factors"]["f4_cancellation"] - 100.0) < 0.05
    assert abs(result["factors"]["f5_response"] - 98.4) < 0.05
    assert abs(result["factors"]["f6_reviews"] - 87.8) < 0.05
    assert abs(result["base"] - 84.19) < 0.01
    assert abs(result["total"] - 84.19) < 0.01


def test_shakib_reproduces_prd_worked_example():
    shakib = TrustInputs(
        phone_verified=True,
        jobs_completed=18, jobs_accepted=30,
        cancellations=([(2, 0, False)] * 3) + ([(48, 0, False)] * 9),
        median_response_seconds=6 * 3600, response_count=30,
        reviews=[(4.8, 0)] * 18,
    )
    result = factors.score(shakib)

    assert abs(result["factors"]["f1_verification"] - 30.0) < 0.05
    assert abs(result["factors"]["f2_volume"] - 63.8) < 0.05
    assert abs(result["factors"]["f3_completion"] - 67.5) < 0.05
    assert abs(result["factors"]["f4_cancellation"] - 16.4) < 0.05
    assert abs(result["factors"]["f5_response"] - 36.0) < 0.05
    assert abs(result["factors"]["f6_reviews"] - 91.7) < 0.05
    assert abs(result["base"] - 53.48) < 0.01


def test_the_product_thesis_holds():
    kamal = TrustInputs(
        phone_verified=True, identity_verified=True, skill_verified=True,
        jobs_completed=4, jobs_accepted=4,
        median_response_seconds=8 * 60, response_count=6,
        reviews=[(4.9, 0)] * 4,
    )
    shakib = TrustInputs(
        phone_verified=True,
        jobs_completed=18, jobs_accepted=30,
        cancellations=([(2, 0, False)] * 3) + ([(48, 0, False)] * 9),
        median_response_seconds=6 * 3600, response_count=30,
        reviews=[(4.8, 0)] * 18,
    )

    kamal_score = factors.score(kamal)
    shakib_score = factors.score(shakib)

    assert shakib_score["factors"]["f6_reviews"] > 90
    assert kamal_score["total"] > shakib_score["total"] + 25
