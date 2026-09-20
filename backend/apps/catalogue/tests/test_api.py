from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalogue.models import Location, Service, ServiceCategory

pytestmark = pytest.mark.django_db

@pytest.fixture
def client():
    return APIClient()

@pytest.fixture
def catalogue():
    electrical = ServiceCategory.objects.create(name="Electrical",
                                                display_order=0)
    plumbing = ServiceCategory.objects.create(name="Plumbing",
                                              display_order=1)
    Service.objects.create(
        category=electrical, name="Ceiling fan installation",
        suggested_price_min=Decimal("500"),
        suggested_price_max=Decimal("1200"),
    )
    Service.objects.create(category=electrical, name="Switchboard repair")
    Service.objects.create(category=plumbing, name="Tap repair")
    return electrical, plumbing

@pytest.fixture
def geography():
    dhaka = Location.objects.create(name="Dhaka", level=Location.Level.CITY)
    dhanmondi = Location.objects.create(name="Dhanmondi",
                                        level=Location.Level.THANA,
                                        parent=dhaka)
    Location.objects.create(name="Dhanmondi 27", level=Location.Level.AREA,
                            parent=dhanmondi)
    return dhaka, dhanmondi

def test_categories_readable_without_authentication(client, catalogue):
    resp = client.get(reverse("catalogue:category-list"))
    assert resp.status_code == 200
    assert len(resp.data) == 2

def test_services_readable_without_authentication(client, catalogue):
    resp = client.get(reverse("catalogue:service-list"))
    assert resp.status_code == 200
    assert resp.data["count"] == 3

def test_locations_readable_without_authentication(client, geography):
    resp = client.get(reverse("catalogue:location-list"))
    assert resp.status_code == 200
    assert len(resp.data) == 3

def test_inactive_category_is_hidden(client, catalogue):
    electrical, _ = catalogue
    electrical.is_active = False
    electrical.save(update_fields=["is_active"])

    resp = client.get(reverse("catalogue:category-list"))
    assert [c["slug"] for c in resp.data] == ["plumbing"]

def test_inactive_service_is_hidden(client, catalogue):
    service = Service.objects.get(slug="tap-repair")
    service.is_active = False
    service.save(update_fields=["is_active"])

    resp = client.get(reverse("catalogue:service-list"))
    assert resp.data["count"] == 2

def test_services_of_inactive_category_are_hidden(client, catalogue):
    electrical, _ = catalogue
    electrical.is_active = False
    electrical.save(update_fields=["is_active"])

    resp = client.get(reverse("catalogue:service-list"))
    assert resp.data["count"] == 1

def test_services_filterable_by_category(client, catalogue):
    resp = client.get(reverse("catalogue:service-list"),
                      {"category": "electrical"})
    assert resp.data["count"] == 2

def test_services_searchable_by_name(client, catalogue):
    resp = client.get(reverse("catalogue:service-list"), {"search": "fan"})
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == "Ceiling fan installation"

def test_locations_filterable_by_level(client, geography):
    resp = client.get(reverse("catalogue:location-list"), {"level": "thana"})
    assert len(resp.data) == 1
    assert resp.data[0]["name"] == "Dhanmondi"

def test_locations_filterable_by_parent(client, geography):
    dhaka, _ = geography
    resp = client.get(reverse("catalogue:location-list"),
                      {"parent": dhaka.pk})
    assert len(resp.data) == 1
    assert resp.data[0]["level"] == "thana"

def test_category_detail_inlines_services(client, catalogue):
    resp = client.get(reverse("catalogue:category-detail",
                              args=["electrical"]))
    assert resp.status_code == 200
    assert len(resp.data["services"]) == 2

def test_category_detail_404_uses_error_envelope(client):
    resp = client.get(reverse("catalogue:category-detail", args=["nope"]))
    assert resp.status_code == 404
    assert resp.data["error"]["code"] == "not_found"

def test_category_list_includes_service_count(client, catalogue):
    resp = client.get(reverse("catalogue:category-list"))
    counts = {c["slug"]: c["service_count"] for c in resp.data}
    assert counts == {"electrical": 2, "plumbing": 1}

def test_service_count_excludes_inactive_services(client, catalogue):
    service = Service.objects.get(slug="switchboard-repair")
    service.is_active = False
    service.save(update_fields=["is_active"])

    resp = client.get(reverse("catalogue:category-list"))
    counts = {c["slug"]: c["service_count"] for c in resp.data}
    assert counts["electrical"] == 1

def test_location_tree_nests_children(client, geography):
    resp = client.get(reverse("catalogue:location-tree"))
    assert resp.status_code == 200

    city = resp.data[0]
    assert city["name"] == "Dhaka"
    assert city["children"][0]["name"] == "Dhanmondi"
    assert city["children"][0]["children"][0]["name"] == "Dhanmondi 27"

def test_location_full_name_includes_parent(client, geography):
    resp = client.get(reverse("catalogue:location-list"), {"level": "thana"})
    assert resp.data[0]["full_name"] == "Dhanmondi, Dhaka"

def test_catalogue_is_not_writable_through_the_api(client, catalogue):
    resp = client.post(reverse("catalogue:category-list"),
                       {"name": "Injected"}, format="json")
    assert resp.status_code in (401, 403, 405)
    assert not ServiceCategory.objects.filter(name="Injected").exists()

def test_categories_returned_in_display_order(client, catalogue):
    ServiceCategory.objects.create(name="Cleaning", display_order=2)

    resp = client.get(reverse("catalogue:category-list"))
    assert [c["slug"] for c in resp.data] == ["electrical", "plumbing",
                                              "cleaning"]

def test_ordering_survives_the_service_count_annotation(client, catalogue):
    from apps.catalogue import selectors
    qs = selectors.active_categories(with_service_count=True)
    assert "ORDER BY" in str(qs.query)
    assert [c.display_order for c in qs] == sorted(
        c.display_order for c in qs
    )
