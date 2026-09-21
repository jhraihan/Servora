from decimal import Decimal

import pytest

from apps.accounts import services as account_services
from apps.accounts.models import ProviderProfile, User
from apps.common.exceptions import NotFound
from apps.trust import engine
from apps.trust.models import TrustSnapshot

pytestmark = pytest.mark.django_db


@pytest.fixture
def provider(db):
    user = account_services.register_user(
        phone="+8801712345678", password="testpass123",
        full_name="Kamal Hossain", role=User.Role.PROVIDER,
    )
    return user.provider_profile


def _set_counters(provider, **fields):
    for name, value in fields.items():
        setattr(provider, name, value)
    provider.save()
    provider.refresh_from_db()
    return provider


def test_new_provider_scores_low_but_not_zero(provider):
    snapshot = engine.recompute(provider.id)
    assert snapshot.score > 0
    assert snapshot.tier == ProviderProfile.Tier.NEW


def test_verification_alone_lifts_a_brand_new_provider(provider):
    before = engine.recompute(provider.id).score

    provider.user.phone_verified = True
    provider.user.save(update_fields=["phone_verified"])
    _set_counters(provider, identity_verified=True, skill_verified=True)

    after = engine.recompute(provider.id).score
    assert after > before + 15


def test_recompute_updates_denormalised_cache(provider):
    _set_counters(provider, jobs_completed=20, jobs_accepted=20,
                  identity_verified=True)
    snapshot = engine.recompute(provider.id)

    provider.refresh_from_db()
    assert provider.trust_score == snapshot.score
    assert provider.trust_tier == snapshot.tier
    assert provider.trust_computed_at is not None


def test_snapshot_records_full_factor_breakdown(provider):
    snapshot = engine.recompute(provider.id)
    payload = snapshot.factors

    assert set(payload["factors"]) == set(engine.factors.WEIGHTS)
    assert "weights" in payload and "weighted" in payload
    assert "base" in payload and "total" in payload
    assert snapshot.algo_version == engine.factors.ALGO_VERSION


def test_every_recompute_appends_a_new_snapshot(provider):
    engine.recompute(provider.id)
    engine.recompute(provider.id)
    engine.recompute(provider.id)
    assert TrustSnapshot.objects.filter(provider=provider).count() == 3


def test_snapshots_are_immutable(provider):
    snapshot = engine.recompute(provider.id)
    snapshot.score = Decimal("99.00")
    with pytest.raises(ValueError):
        snapshot.save()


def test_snapshots_cannot_be_deleted(provider):
    snapshot = engine.recompute(provider.id)
    with pytest.raises(ValueError):
        snapshot.delete()


def test_recompute_records_its_trigger(provider):
    engine.recompute(provider.id,
                     trigger=TrustSnapshot.Trigger.BOOKING_COMPLETED)
    snapshot = TrustSnapshot.objects.filter(provider=provider).first()
    assert snapshot.trigger == TrustSnapshot.Trigger.BOOKING_COMPLETED


def test_recompute_unknown_provider_raises(db):
    with pytest.raises(NotFound):
        engine.recompute(99999)


def test_recompute_all_covers_every_active_provider(db):
    for n in range(3):
        account_services.register_user(
            phone="+88017123456%02d" % n, password="testpass123",
            role=User.Role.PROVIDER,
        )
    count = engine.recompute_all()
    assert count == 3
    assert TrustSnapshot.objects.count() == 3


def test_recompute_all_skips_inactive_users(db):
    user = account_services.register_user(
        phone="+8801712345678", password="testpass123",
        role=User.Role.PROVIDER,
    )
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert engine.recompute_all() == 0


@pytest.mark.parametrize("score,jobs,verified,expected", [
    (95, 2, True, ProviderProfile.Tier.NEW),
    (95, 30, True, ProviderProfile.Tier.TRUSTED_PRO),
    (95, 30, False, ProviderProfile.Tier.RISING),
    (95, 20, True, ProviderProfile.Tier.ESTABLISHED),
    (75, 15, True, ProviderProfile.Tier.ESTABLISHED),
    (75, 5, True, ProviderProfile.Tier.RISING),
    (60, 30, True, ProviderProfile.Tier.RISING),
    (20, 30, True, ProviderProfile.Tier.RISING),
])
def test_tier_gates(score, jobs, verified, expected):
    assert engine.resolve_tier(
        score, jobs_completed=jobs, identity_verified=verified,
    ) == expected


def test_investigation_overrides_every_other_tier():
    assert engine.resolve_tier(
        99, jobs_completed=500, identity_verified=True,
        under_investigation=True,
    ) == ProviderProfile.Tier.UNDER_REVIEW


def test_high_score_low_volume_stays_below_established(provider):
    provider.user.phone_verified = True
    provider.user.save(update_fields=["phone_verified"])
    _set_counters(provider, identity_verified=True, skill_verified=True,
                  jobs_completed=4, jobs_accepted=4,
                  median_response_seconds=8 * 60, requests_received=6)

    snapshot = engine.recompute(provider.id)

    assert snapshot.score > 70
    assert snapshot.tier == ProviderProfile.Tier.RISING


def test_low_scoring_veteran_is_flagged_for_review():
    assert engine.needs_admin_review(35, 20) is True
    assert engine.needs_admin_review(35, 5) is False
    assert engine.needs_admin_review(60, 20) is False


def test_cancellations_lower_the_score(provider):
    _set_counters(provider, jobs_completed=20, jobs_accepted=20)
    clean = engine.recompute(provider.id).score

    _set_counters(provider, jobs_completed=20, jobs_accepted=30,
                  jobs_cancelled=10)
    messy = engine.recompute(provider.id).score

    assert messy < clean


def test_breakdown_exposes_all_six_factors(provider):
    engine.recompute(provider.id)
    provider.refresh_from_db()

    data = engine.breakdown(provider)
    assert len(data["factors"]) == 6
    assert {f["key"] for f in data["factors"]} == set(engine.factors.WEIGHTS)
    for entry in data["factors"]:
        assert "label" in entry and "score" in entry
        assert "weight" in entry and "contribution" in entry


def test_breakdown_reports_raw_evidence_not_just_a_number(provider):
    _set_counters(provider, jobs_completed=18, jobs_accepted=30,
                  jobs_cancelled=12, median_response_seconds=6 * 3600)
    engine.recompute(provider.id)
    provider.refresh_from_db()

    evidence = engine.breakdown(provider)["evidence"]
    assert evidence["jobs_completed"] == 18
    assert evidence["completion_rate"] == 60.0
    assert evidence["cancellation_rate"] == 40.0
    assert evidence["median_response_seconds"] == 6 * 3600


def test_breakdown_completion_rate_handles_zero_jobs(provider):
    engine.recompute(provider.id)
    provider.refresh_from_db()
    assert engine.breakdown(provider)["evidence"]["completion_rate"] is None


def test_score_history_is_chartable(provider):
    engine.recompute(provider.id)
    _set_counters(provider, jobs_completed=10, jobs_accepted=10)
    engine.recompute(provider.id)
    _set_counters(provider, jobs_completed=30, jobs_accepted=30)
    engine.recompute(provider.id)

    history = list(
        TrustSnapshot.objects
        .filter(provider=provider)
        .order_by("created_at")
        .values_list("score", flat=True)
    )
    assert history == sorted(history)


def test_verification_approval_triggers_recompute(provider, django_capture_on_commit_callbacks):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.providers import services as provider_services

    admin = User.objects.create_superuser(
        phone="+8801655554444", password="adminpass123",
    )
    doc = provider_services.submit_verification_document(
        provider_id=provider.id, document_type="trade_certificate",
        file=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
    )

    with django_capture_on_commit_callbacks(execute=True):
        provider_services.decide_verification(
            document_id=doc.id, reviewer_id=admin.id, approve=True,
        )

    snapshot = TrustSnapshot.objects.filter(provider=provider).first()
    assert snapshot is not None
    assert snapshot.trigger == TrustSnapshot.Trigger.VERIFICATION_DECIDED

    provider.refresh_from_db()
    assert provider.skill_verified is True
    assert provider.trust_score == snapshot.score


def test_approval_raises_the_score(provider, django_capture_on_commit_callbacks):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.providers import services as provider_services

    admin = User.objects.create_superuser(
        phone="+8801655553333", password="adminpass123",
    )
    before = engine.recompute(provider.id).score

    doc = provider_services.submit_verification_document(
        provider_id=provider.id, document_type="trade_certificate",
        file=SimpleUploadedFile("c.jpg", b"x", content_type="image/jpeg"),
    )
    with django_capture_on_commit_callbacks(execute=True):
        provider_services.decide_verification(
            document_id=doc.id, reviewer_id=admin.id, approve=True,
        )

    provider.refresh_from_db()
    assert provider.trust_score > before
