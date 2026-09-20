import pytest
from django.core.management import call_command

from apps.catalogue.models import Location, Service, ServiceCategory
from apps.catalogue.seed_data import CATEGORIES, DHAKA

pytestmark = pytest.mark.django_db

@pytest.fixture
def seeded():
    call_command("seed_catalogue", verbosity=0)

def test_seeds_all_eight_launch_categories(seeded):
    assert ServiceCategory.objects.count() == 8

def test_category_names_match_the_prd(seeded):
    expected = {
        "Electrical", "Plumbing", "AC & Refrigeration", "Computer & IT",
        "Painting", "Cleaning", "Appliance Repair", "Car Mechanic",
    }
    assert set(ServiceCategory.objects.values_list("name", flat=True)) \
        == expected

def test_every_category_has_services(seeded):
    for category in ServiceCategory.objects.all():
        assert category.services.exists(), \
            "%s has no services" % category.name

def test_service_count_matches_seed_data(seeded):
    expected = sum(len(services) for _, _, _, services in CATEGORIES)
    assert Service.objects.count() == expected

def test_seeds_dhaka_with_full_tree(seeded):
    city = Location.objects.get(level=Location.Level.CITY)
    assert city.name == "Dhaka"
    assert city.children.count() == len(DHAKA["thanas"])

def test_every_thana_has_areas(seeded):
    for thana in Location.objects.filter(level=Location.Level.THANA):
        assert thana.children.exists(), "%s has no areas" % thana.name

def test_every_location_has_coordinates(seeded):
    assert not Location.objects.filter(
        latitude__isnull=True
    ).exists()

def test_price_bands_are_ordered_where_present(seeded):
    for service in Service.objects.exclude(suggested_price_min=None) \
                                  .exclude(suggested_price_max=None):
        assert service.suggested_price_max >= service.suggested_price_min

def test_visit_quote_services_may_have_no_band(seeded):
    wiring = Service.objects.get(slug="house-wiring")
    assert wiring.pricing_model == Service.PricingModel.VISIT_QUOTE
    assert wiring.suggested_price_min is None

def test_reseeding_creates_no_duplicates(seeded):
    before = (ServiceCategory.objects.count(), Service.objects.count(),
              Location.objects.count())
    call_command("seed_catalogue", verbosity=0)
    after = (ServiceCategory.objects.count(), Service.objects.count(),
             Location.objects.count())
    assert before == after

def test_reseeding_applies_edits_in_place(seeded):
    service = Service.objects.get(slug="ceiling-fan-installation")
    original_id = service.pk

    service.name = "Edited by hand"
    service.save(update_fields=["name"])

    call_command("seed_catalogue", verbosity=0)

    service.refresh_from_db()
    assert service.pk == original_id
    assert service.name == "Ceiling fan installation"

def test_skip_locations_flag(db):
    call_command("seed_catalogue", "--skip-locations", verbosity=0)
    assert ServiceCategory.objects.exists()
    assert not Location.objects.exists()
