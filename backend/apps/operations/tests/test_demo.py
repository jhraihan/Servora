from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import ProviderProfile
from apps.operations import demo
from apps.payments import services as payment_services
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def catalogue(db):
    call_command("seed_catalogue", verbosity=0)


def test_refuses_to_run_without_debug(settings, catalogue):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo", stdout=StringIO())
    assert not User.objects.filter(phone__startswith=demo.DEMO_PREFIX).exists()


def test_marketplace_is_internally_consistent(settings, catalogue):
    settings.DEBUG = True
    call_command("seed_demo", "--per-archetype", "1", stdout=StringIO())

    providers = ProviderProfile.objects.filter(
        user__phone__startswith=demo.DEMO_PREFIX)
    assert providers.count() == len(demo.ARCHETYPES)

    for provider in providers:
        assert payment_services.reconcile_provider(provider.pk) == []
        assert provider.trust_computed_at is not None

    assert Review.objects.filter(published_at__isnull=False).exists()


def test_archetypes_rank_the_way_the_prd_argues(settings, catalogue):
    settings.DEBUG = True
    call_command("seed_demo", "--per-archetype", "1", stdout=StringIO())

    by_role = {
        a.key: ProviderProfile.objects.get(user__phone=demo.demo_phone(i + 1))
        for i, a in enumerate(demo.ARCHETYPES)
    }
    flaky_reviews = Review.objects.filter(provider=by_role["flaky"])
    average_stars = sum(r.rating for r in flaky_reviews) / flaky_reviews.count()

    assert average_stars >= 4.5
    assert by_role["veteran"].trust_score > by_role["flaky"].trust_score
    assert by_role["newcomer"].trust_score > by_role["flaky"].trust_score
    assert by_role["veteran"].trust_tier == ProviderProfile.Tier.TRUSTED_PRO


def test_reseeding_is_idempotent(settings, catalogue):
    settings.DEBUG = True
    call_command("seed_demo", "--per-archetype", "1", stdout=StringIO())
    before = User.objects.filter(phone__startswith=demo.DEMO_PREFIX).count()
    call_command("seed_demo", "--per-archetype", "1", stdout=StringIO())
    assert User.objects.filter(phone__startswith=demo.DEMO_PREFIX).count() == before


def test_reset_removes_every_demo_row(settings, catalogue):
    settings.DEBUG = True
    call_command("seed_demo", "--per-archetype", "1", stdout=StringIO())
    assert demo.reset_demo() > 0
    assert not User.objects.filter(phone__startswith=demo.DEMO_PREFIX).exists()


def test_bulk_providers_are_searchable_and_scored(settings, catalogue):
    settings.DEBUG = True
    call_command("seed_demo", "--per-archetype", "0", "--bulk", "25",
                 stdout=StringIO())

    bulk = ProviderProfile.objects.filter(
        user__phone__startswith=demo.DEMO_PREFIX)
    assert bulk.count() == 25
    assert not bulk.filter(trust_computed_at__isnull=True).exists()
    assert all(p.offerings.exists() and p.service_areas.exists() for p in bulk)


def test_first_round_uses_the_prd_cast(settings, catalogue):
    settings.DEBUG = True
    call_command("seed_demo", "--per-archetype", "1", stdout=StringIO())

    assert ProviderProfile.objects.get(
        user__phone=demo.demo_phone(2)).display_name == "Kamal Hossain"
    assert ProviderProfile.objects.get(
        user__phone=demo.demo_phone(3)).display_name == "Shakib Rahman"
