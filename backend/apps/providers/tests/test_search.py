from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts import services as account_services
from apps.accounts.models import ProviderProfile, User
from apps.providers import search, services

pytestmark = pytest.mark.django_db


@pytest.fixture
def anon():
    return APIClient()


def _make_provider(phone, name, *, service, location, price="1800",
                   trust=Decimal("50.00"),
                   tier=ProviderProfile.Tier.RISING,
                   identity_verified=False, accepting=True, weekdays=None):
    user = account_services.register_user(
        phone=phone, password="testpass123", full_name=name,
        role=User.Role.PROVIDER,
    )
    provider = user.provider_profile
    provider.trust_score = trust
    provider.trust_tier = tier
    provider.identity_verified = identity_verified
    provider.is_accepting_work = accepting
    provider.save()

    services.add_offering(provider_id=provider.id, service_id=service.id,
                          price=Decimal(price))
    services.set_service_areas(provider_id=provider.id,
                               location_ids=[location.id])

    if weekdays is not None:
        services.set_weekly_availability(
            provider_id=provider.id,
            windows=[{"weekday": d, "start_time": time(9, 0),
                      "end_time": time(17, 0)} for d in weekdays],
        )
    return provider


def test_search_requires_nothing_but_returns_active_providers(
        service, dhanmondi):
    _make_provider("+8801712345601", "A", service=service,
                   location=dhanmondi)
    results = list(search.search_providers())
    assert len(results) == 1


def test_search_filters_by_service(service, second_service, dhanmondi):
    a = _make_provider("+8801712345601", "A", service=service,
                       location=dhanmondi)
    _make_provider("+8801712345602", "B", service=second_service,
                   location=dhanmondi)

    results = list(search.search_providers(service_id=service.id))
    assert [p.id for p in results] == [a.id]


def test_search_filters_by_location(service, dhanmondi, gulshan):
    a = _make_provider("+8801712345601", "A", service=service,
                       location=dhanmondi)
    _make_provider("+8801712345602", "B", service=service, location=gulshan)

    results = list(search.search_providers(location_id=dhanmondi.id))
    assert [p.id for p in results] == [a.id]


def test_thana_provider_matches_request_in_its_area(service, dhaka,
                                                     dhanmondi):
    from apps.catalogue.models import Location
    area = Location.objects.create(name="Dhanmondi 27",
                                   level=Location.Level.AREA,
                                   parent=dhanmondi)
    provider = _make_provider("+8801712345601", "A", service=service,
                              location=dhanmondi)

    results = list(search.search_providers(location_id=area.id))
    assert [p.id for p in results] == [provider.id]


def test_default_ordering_is_trust_descending(service, dhanmondi):
    low = _make_provider("+8801712345601", "Low", service=service,
                         location=dhanmondi, trust=Decimal("40.00"))
    high = _make_provider("+8801712345602", "High", service=service,
                          location=dhanmondi, trust=Decimal("88.00"))
    mid = _make_provider("+8801712345603", "Mid", service=service,
                         location=dhanmondi, trust=Decimal("65.00"))

    results = list(search.search_providers())
    assert [p.id for p in results] == [high.id, mid.id, low.id]


def test_verified_outranks_unverified_at_equal_trust(service, dhanmondi):
    unverified = _make_provider("+8801712345601", "Unverified",
                                service=service, location=dhanmondi,
                                trust=Decimal("70.00"),
                                identity_verified=False)
    verified = _make_provider("+8801712345602", "Verified", service=service,
                              location=dhanmondi, trust=Decimal("70.00"),
                              identity_verified=True)

    results = list(search.search_providers())
    assert [p.id for p in results] == [verified.id, unverified.id]


def test_unverified_still_appears_in_results(service, dhanmondi):
    _make_provider("+8801712345601", "Unverified", service=service,
                   location=dhanmondi, identity_verified=False)
    assert len(list(search.search_providers())) == 1


def test_price_sort_ascending(service, dhanmondi):
    expensive = _make_provider("+8801712345601", "Expensive", service=service,
                               location=dhanmondi, price="3000")
    cheap = _make_provider("+8801712345602", "Cheap", service=service,
                           location=dhanmondi, price="900")

    results = list(search.search_providers(ordering=search.SORT_PRICE))
    assert [p.id for p in results] == [cheap.id, expensive.id]


def test_search_exposes_matching_price(service, dhanmondi):
    _make_provider("+8801712345601", "A", service=service,
                   location=dhanmondi, price="2400")
    provider = list(search.search_providers(service_id=service.id))[0]
    assert provider.matched_price == Decimal("2400")


def test_price_range_filter(service, dhanmondi):
    _make_provider("+8801712345601", "Cheap", service=service,
                   location=dhanmondi, price="900")
    mid = _make_provider("+8801712345602", "Mid", service=service,
                         location=dhanmondi, price="1800")
    _make_provider("+8801712345603", "Expensive", service=service,
                   location=dhanmondi, price="5000")

    results = list(search.search_providers(price_min=Decimal("1000"),
                                           price_max=Decimal("2500")))
    assert [p.id for p in results] == [mid.id]


def test_min_trust_filter(service, dhanmondi):
    _make_provider("+8801712345601", "Low", service=service,
                   location=dhanmondi, trust=Decimal("30.00"))
    high = _make_provider("+8801712345602", "High", service=service,
                          location=dhanmondi, trust=Decimal("80.00"))

    results = list(search.search_providers(min_trust=Decimal("50")))
    assert [p.id for p in results] == [high.id]


def test_tier_filter(service, dhanmondi):
    _make_provider("+8801712345601", "Rising", service=service,
                   location=dhanmondi, tier=ProviderProfile.Tier.RISING)
    established = _make_provider(
        "+8801712345602", "Established", service=service, location=dhanmondi,
        tier=ProviderProfile.Tier.ESTABLISHED,
    )

    results = list(search.search_providers(
        tier=ProviderProfile.Tier.ESTABLISHED
    ))
    assert [p.id for p in results] == [established.id]


def test_verified_only_filter(service, dhanmondi):
    _make_provider("+8801712345601", "Unverified", service=service,
                   location=dhanmondi, identity_verified=False)
    verified = _make_provider("+8801712345602", "Verified", service=service,
                              location=dhanmondi, identity_verified=True)

    results = list(search.search_providers(verified_only=True))
    assert [p.id for p in results] == [verified.id]


def test_providers_not_accepting_work_are_hidden(service, dhanmondi):
    _make_provider("+8801712345601", "Paused", service=service,
                   location=dhanmondi, accepting=False)
    assert list(search.search_providers()) == []


def test_providers_under_review_are_hidden(service, dhanmondi):
    _make_provider("+8801712345601", "Flagged", service=service,
                   location=dhanmondi,
                   tier=ProviderProfile.Tier.UNDER_REVIEW)
    assert list(search.search_providers()) == []


def test_suspended_providers_are_hidden(service, dhanmondi):
    from django.utils import timezone
    provider = _make_provider("+8801712345601", "Suspended", service=service,
                              location=dhanmondi)
    provider.user.suspended_at = timezone.now()
    provider.user.save(update_fields=["suspended_at"])

    assert list(search.search_providers()) == []


def test_inactive_offerings_do_not_match(service, dhanmondi):
    provider = _make_provider("+8801712345601", "A", service=service,
                              location=dhanmondi)
    offering = provider.offerings.first()
    services.update_offering(provider_id=provider.id,
                             offering_id=offering.id, is_active=False)

    assert list(search.search_providers(service_id=service.id)) == []


def test_availability_filter_matches_weekly_pattern(service, dhanmondi):
    monday = _next_weekday(0)
    available = _make_provider("+8801712345601", "Monday", service=service,
                               location=dhanmondi, weekdays=[0])
    _make_provider("+8801712345602", "Tuesday", service=service,
                   location=dhanmondi, weekdays=[1])

    results = list(search.search_providers(available_on=monday))
    assert [p.id for p in results] == [available.id]


def test_leave_exception_removes_from_availability_search(service,
                                                          dhanmondi):
    monday = _next_weekday(0)
    provider = _make_provider("+8801712345601", "OnLeave", service=service,
                              location=dhanmondi, weekdays=[0])
    services.set_availability_exception(
        provider_id=provider.id, date=monday, is_available=False,
    )
    assert list(search.search_providers(available_on=monday)) == []


def test_extra_day_exception_adds_to_availability_search(service, dhanmondi):
    friday = _next_weekday(4)
    provider = _make_provider("+8801712345601", "ExtraDay", service=service,
                              location=dhanmondi, weekdays=[0])
    services.set_availability_exception(
        provider_id=provider.id, date=friday, is_available=True,
        start_time=time(10, 0), end_time=time(14, 0),
    )

    results = list(search.search_providers(available_on=friday))
    assert [p.id for p in results] == [provider.id]


def test_search_endpoint_is_public(anon, service, dhanmondi):
    _make_provider("+8801712345601", "A", service=service,
                   location=dhanmondi)
    resp = anon.get(reverse("providers:search"))
    assert resp.status_code == 200
    assert resp.data["count"] == 1


def test_search_endpoint_is_paginated(anon, service, dhanmondi):
    for n in range(3):
        _make_provider("+88017123456%02d" % n, "P%d" % n, service=service,
                       location=dhanmondi)

    resp = anon.get(reverse("providers:search"), {"page_size": 2})
    assert len(resp.data["results"]) == 2
    assert resp.data["next"] is not None


def test_search_result_carries_trust_facts_not_just_score(anon, service,
                                                           dhanmondi):
    _make_provider("+8801712345601", "A", service=service,
                   location=dhanmondi)
    resp = anon.get(reverse("providers:search"))
    row = resp.data["results"][0]

    for field in ["trust_score", "trust_tier", "identity_verified",
                  "jobs_completed", "jobs_cancelled",
                  "median_response_seconds", "from_price"]:
        assert field in row


def test_search_endpoint_applies_filters(anon, service, dhanmondi):
    _make_provider("+8801712345601", "Low", service=service,
                   location=dhanmondi, trust=Decimal("20.00"))
    _make_provider("+8801712345602", "High", service=service,
                   location=dhanmondi, trust=Decimal("90.00"))

    resp = anon.get(reverse("providers:search"), {"min_trust": "50"})
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["display_name"] == "High"


def test_search_endpoint_ignores_malformed_filters(anon, service, dhanmondi):
    _make_provider("+8801712345601", "A", service=service,
                   location=dhanmondi)
    resp = anon.get(reverse("providers:search"), {
        "min_trust": "not-a-number", "location": "abc",
        "available_on": "nonsense",
    })
    assert resp.status_code == 200
    assert resp.data["count"] == 1


def _next_weekday(weekday):
    today = date.today()
    offset = (weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=offset)


def test_search_query_count_is_constant(django_assert_num_queries, service,
                                        dhanmondi):
    from apps.providers.serializers import ProviderSearchResultSerializer

    for n in range(2):
        _make_provider("+88017123456%02d" % n, "P%d" % n, service=service,
                       location=dhanmondi)

    with django_assert_num_queries(2):
        ProviderSearchResultSerializer(
            list(search.search_providers()), many=True,
        ).data

    for n in range(2, 8):
        _make_provider("+88017123456%02d" % n, "P%d" % n, service=service,
                       location=dhanmondi)

    with django_assert_num_queries(2):
        ProviderSearchResultSerializer(
            list(search.search_providers()), many=True,
        ).data


def test_search_is_rate_limited_per_ip(anon):
    url = reverse("providers:search")
    for _ in range(100):
        assert anon.get(url).status_code == 200
    assert anon.get(url).status_code == 429
