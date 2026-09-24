from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts import services as account_services
from apps.accounts.models import User
from apps.bookings import services as booking_services
from apps.catalogue.models import Location, Service, ServiceCategory
from apps.providers import services as provider_services


@pytest.fixture
def service(db):
    category = ServiceCategory.objects.create(name="AC & Refrigeration")
    return Service.objects.create(
        category=category, name="AC servicing",
        suggested_price_min=Decimal("1200"),
        suggested_price_max=Decimal("2500"),
    )


@pytest.fixture
def dhanmondi(db):
    dhaka = Location.objects.create(name="Dhaka", level=Location.Level.CITY)
    return Location.objects.create(name="Dhanmondi",
                                   level=Location.Level.THANA, parent=dhaka)


@pytest.fixture
def customer_user(db):
    return account_services.register_user(
        phone="+8801912345678", password="testpass123",
        full_name="Rumana Akter", role=User.Role.CUSTOMER,
    )


@pytest.fixture
def customer(customer_user):
    return customer_user.customer_profile


@pytest.fixture
def provider_user(db):
    return account_services.register_user(
        phone="+8801712345678", password="testpass123",
        full_name="Kamal Hossain", role=User.Role.PROVIDER,
    )


@pytest.fixture
def provider(provider_user, service, dhanmondi):
    profile = provider_user.provider_profile
    provider_services.add_offering(provider_id=profile.id,
                                   service_id=service.id,
                                   price=Decimal("1800"))
    provider_services.set_service_areas(provider_id=profile.id,
                                        location_ids=[dhanmondi.id])
    return profile


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(phone="+8801611112222",
                                         password="adminpass123")


@pytest.fixture
def complete_job(customer, provider, service, dhanmondi,
                 django_capture_on_commit_callbacks):
    def _complete(final_price="2000", confirmed_price=None):
        start = timezone.now() + timezone.timedelta(days=2)
        request = booking_services.create_request(
            customer_id=customer.id, service_id=service.id,
            location_id=dhanmondi.id, address="House 12",
            description="AC not cooling", preferred_start=start,
            preferred_end=start + timezone.timedelta(hours=3),
        )
        booking = booking_services.respond_to_request(
            request_id=request.id, provider_id=provider.id, accept=True,
        )
        booking_services.start_job(booking_id=booking.id,
                                   provider_id=provider.id)
        booking_services.complete_job(booking_id=booking.id,
                                      provider_id=provider.id,
                                      final_price=Decimal(final_price))
        with django_capture_on_commit_callbacks(execute=True):
            return booking_services.confirm_completion(
                booking_id=booking.id, customer_id=customer.id,
                confirmed_price=(Decimal(confirmed_price)
                                 if confirmed_price is not None else None),
            )
    return _complete
