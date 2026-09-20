from decimal import Decimal

import pytest

from apps.accounts import services as account_services
from apps.accounts.models import ProviderProfile, User
from apps.catalogue.models import Location, Service, ServiceCategory


@pytest.fixture
def provider_user(db):
    return account_services.register_user(
        phone="+8801712345678", password="testpass123",
        full_name="Kamal Hossain", role=User.Role.PROVIDER,
    )


@pytest.fixture
def provider(provider_user):
    return provider_user.provider_profile


@pytest.fixture
def other_provider(db):
    user = account_services.register_user(
        phone="+8801812345678", password="testpass123",
        full_name="Shakib Rahman", role=User.Role.PROVIDER,
    )
    return user.provider_profile


@pytest.fixture
def customer_user(db):
    return account_services.register_user(
        phone="+8801912345678", password="testpass123",
        full_name="Rumana Akter", role=User.Role.CUSTOMER,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        phone="+8801612345678", password="adminpass123",
    )


@pytest.fixture
def category(db):
    return ServiceCategory.objects.create(name="AC & Refrigeration")


@pytest.fixture
def service(category):
    return Service.objects.create(
        category=category, name="AC servicing",
        suggested_price_min=Decimal("1200"),
        suggested_price_max=Decimal("2500"),
        typical_duration_minutes=90,
    )


@pytest.fixture
def second_service(category):
    return Service.objects.create(
        category=category, name="AC gas refill",
        suggested_price_min=Decimal("2500"),
        suggested_price_max=Decimal("5000"),
    )


@pytest.fixture
def dhaka(db):
    return Location.objects.create(name="Dhaka", level=Location.Level.CITY)


@pytest.fixture
def dhanmondi(dhaka):
    return Location.objects.create(name="Dhanmondi",
                                   level=Location.Level.THANA, parent=dhaka)


@pytest.fixture
def gulshan(dhaka):
    return Location.objects.create(name="Gulshan",
                                   level=Location.Level.THANA, parent=dhaka)
