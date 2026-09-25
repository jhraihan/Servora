import random
from dataclasses import dataclass
from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from apps.accounts import services as account_services
from apps.accounts.models import ProviderProfile
from apps.bookings import services as booking_services
from apps.bookings.models import Booking, BookingEvent, ProviderResponse, ServiceRequest
from apps.catalogue.models import Location, Service
from apps.payments.models import LedgerEntry, Payment
from apps.providers import services as provider_services
from apps.providers.models import Availability, ProviderService, ServiceArea
from apps.reviews import services as review_services
from apps.reviews.models import CustomerRating, Review
from apps.trust import engine

User = get_user_model()

DEMO_PREFIX = "+88013000"
DEMO_PASSWORD = "demo-pass-2026"
CUSTOMER_OFFSET = 50000
BULK_OFFSET = 60000

FIRST_NAMES = [
    "Kamal", "Shakib", "Rafiq", "Jamal", "Hasan", "Nasir", "Tareq", "Mizan",
    "Sohel", "Arif", "Imran", "Rubel", "Faruk", "Liton", "Sumon", "Anwar",
]
LAST_NAMES = [
    "Hossain", "Rahman", "Ahmed", "Uddin", "Islam", "Karim", "Mia", "Sarker",
    "Chowdhury", "Talukder", "Molla", "Bhuiyan",
]
FEATURED_NAMES = {
    1: "Rafiq Ahmed",
    2: "Kamal Hossain",
    3: "Shakib Rahman",
    4: "Hasan Islam",
    5: "Nasir Uddin",
    6: "Tareq Mia",
}

CUSTOMER_NAMES = [
    "Rumana Akter", "Farhana Islam", "Nusrat Jahan", "Tanvir Hasan",
    "Sabrina Kabir", "Mahmud Hasan", "Ayesha Siddiqua", "Rezaul Karim",
    "Shirin Sultana", "Fahim Ahmed", "Lamia Rahman", "Nabil Chowdhury",
]


@dataclass(frozen=True)
class Archetype:
    key: str
    completed: int
    early_cancels: int
    late_cancels: int
    declines: int
    response_minutes: int
    ratings: tuple
    phone: bool
    identity: bool
    skill: bool
    experience: int


ARCHETYPES = (
    Archetype("veteran", 26, 1, 0, 2, 6, (5, 5, 5, 4, 5), True, True, True, 15),
    Archetype("newcomer", 4, 0, 0, 0, 8, (5,), True, True, True, 14),
    Archetype("flaky", 14, 5, 3, 6, 360, (5, 5, 4, 5), True, False, False, 6),
    Archetype("steady", 12, 1, 0, 1, 25, (4, 5, 4), True, True, False, 8),
    Archetype("average", 9, 1, 1, 2, 120, (3, 4, 4, 3), True, False, False, 5),
    Archetype("unverified", 0, 0, 0, 0, 0, (), False, False, False, 1),
)


def demo_phone(n):
    return "%s%05d" % (DEMO_PREFIX, n)


def _thanas():
    return list(
        Location.objects.filter(level=Location.Level.THANA, is_active=True)
        .order_by("name")
    )


def _price_for(service, rng):
    if service.suggested_price_min and service.suggested_price_max:
        low, high = int(service.suggested_price_min), int(service.suggested_price_max)
        return Decimal(rng.randrange(low, high + 1, 50) if high > low else low)
    return Decimal(rng.choice([800, 1200, 1500, 2000, 2500]))


def _customers(count):
    customers = []
    for i in range(count):
        phone = demo_phone(CUSTOMER_OFFSET + i)
        user = User.objects.filter(phone=phone).first()
        if user is None:
            user = account_services.register_user(
                phone=phone, password=DEMO_PASSWORD,
                full_name=CUSTOMER_NAMES[i % len(CUSTOMER_NAMES)],
                role=User.Role.CUSTOMER,
            )
        customers.append(user.customer_profile)
    return customers


def _set_up_provider(n, archetype, services, thana, rng):
    name = FEATURED_NAMES.get(n) or "%s %s" % (
        FIRST_NAMES[n % len(FIRST_NAMES)], LAST_NAMES[(n * 7) % len(LAST_NAMES)])
    user = account_services.register_user(
        phone=demo_phone(n), password=DEMO_PASSWORD, full_name=name,
        role=User.Role.PROVIDER,
    )
    if archetype.phone:
        User.objects.filter(pk=user.pk).update(phone_verified=True)

    profile = user.provider_profile
    ProviderProfile.objects.filter(pk=profile.pk).update(
        identity_verified=archetype.identity,
        skill_verified=archetype.skill,
        experience_years=archetype.experience,
        bio="%d years fixing homes across %s." % (archetype.experience, thana.name),
    )

    for service in services:
        provider_services.add_offering(provider_id=profile.pk,
                                       service_id=service.pk,
                                       price=_price_for(service, rng))
    provider_services.set_service_areas(provider_id=profile.pk,
                                        location_ids=[thana.pk])
    provider_services.set_weekly_availability(
        provider_id=profile.pk,
        windows=[{"weekday": d, "start_time": time(9), "end_time": time(18)}
                 for d in range(6)],
    )
    return profile


def _request(customer, service, thana, provider, *, hours_ahead):
    start = timezone.now() + timezone.timedelta(hours=hours_ahead)
    return booking_services.create_request(
        customer_id=customer.pk, service_id=service.pk, location_id=thana.pk,
        address="House %d, Road %d, %s" % (random.randint(1, 90),
                                          random.randint(1, 30), thana.name),
        description="%s needed. Please bring the usual tools." % service.name,
        preferred_start=start,
        preferred_end=start + timezone.timedelta(hours=3),
        target_provider_id=provider.pk,
    )


def _history(profile, archetype, services, thana, customers, rng):
    turn = rng.randrange(len(customers))

    def next_customer():
        nonlocal turn
        turn += 1
        return customers[turn % len(customers)]

    for i in range(archetype.completed):
        customer = next_customer()
        service = services[i % len(services)]
        price = ProviderService.objects.get(provider=profile, service=service).price
        request = _request(customer, service, thana, profile, hours_ahead=48)
        booking = booking_services.respond_to_request(
            request_id=request.pk, provider_id=profile.pk, accept=True)
        booking_services.start_job(booking_id=booking.pk, provider_id=profile.pk)
        booking_services.complete_job(booking_id=booking.pk,
                                      provider_id=profile.pk, final_price=price)
        booking_services.confirm_completion(booking_id=booking.pk,
                                            customer_id=customer.pk,
                                            confirmed_price=price)
        if archetype.ratings:
            rating = archetype.ratings[i % len(archetype.ratings)]
            review_services.create_review(
                booking_id=booking.pk, customer_id=customer.pk, rating=rating,
                punctuality=rating, quality=rating, professionalism=rating,
                price_fairness=max(rating - rng.randint(0, 1), 1),
                comment=rng.choice([
                    "Arrived on time and explained the fault clearly.",
                    "Tidy work, fair price.",
                    "Fixed it in one visit.",
                    "Good job, would book again.",
                    "Took a while but the result is solid.",
                ]),
            )
            review_services.rate_customer(booking_id=booking.pk,
                                          provider_id=profile.pk,
                                          rating=rng.choice([4, 5]))

    for hours_ahead, count in ((72, archetype.early_cancels),
                               (2, archetype.late_cancels)):
        for _ in range(count):
            customer = next_customer()
            request = _request(customer, services[0], thana, profile,
                               hours_ahead=hours_ahead)
            booking = booking_services.respond_to_request(
                request_id=request.pk, provider_id=profile.pk, accept=True)
            booking_services.cancel_booking(
                booking_id=booking.pk, actor=BookingEvent.Actor.PROVIDER,
                actor_user_id=profile.user_id, reason="Could not make it.",
                provider_id=profile.pk,
            )

    for _ in range(archetype.declines):
        request = _request(next_customer(), services[0], thana, profile,
                           hours_ahead=48)
        booking_services.respond_to_request(
            request_id=request.pk, provider_id=profile.pk, accept=False,
            reason="Fully booked.")

    if archetype.response_minutes:
        for response in ProviderResponse.objects.filter(provider=profile):
            jitter = rng.uniform(0.6, 1.4)
            ProviderResponse.objects.filter(pk=response.pk).update(
                response_seconds=int(archetype.response_minutes * 60 * jitter))
        booking_services.refresh_median_response(profile.pk)

    engine.recompute(profile.pk)


def seed_marketplace(*, providers_per_archetype=3, seed=2026, log=print):
    rng = random.Random(seed)
    random.seed(seed)
    thanas = _thanas()
    services = list(Service.objects.filter(is_active=True).select_related(
        "category").order_by("category__display_order", "display_order"))
    if not thanas or not services:
        raise RuntimeError("Run seed_catalogue first.")

    customers = _customers(len(CUSTOMER_NAMES))
    created = 0
    n = 0
    for round_index in range(providers_per_archetype):
        for archetype in ARCHETYPES:
            n += 1
            if User.objects.filter(phone=demo_phone(n)).exists():
                continue
            category = services[(n * 5) % len(services)].category
            offered = [s for s in services if s.category_id == category.pk][:3]
            thana = thanas[(n + round_index) % len(thanas)]
            profile = _set_up_provider(n, archetype, offered, thana, rng)
            _history(profile, archetype, offered, thana, customers, rng)
            profile.refresh_from_db()
            log("  %-22s %-11s trust %6s  %s" % (
                profile.display_name, archetype.key, profile.trust_score,
                profile.trust_tier))
            created += 1
    return created


def seed_bulk(count, *, seed=7, log=print):
    rng = random.Random(seed)
    thanas = _thanas()
    services = list(Service.objects.filter(is_active=True))
    unusable = make_password(None)

    existing = set(
        User.objects.filter(phone__startswith=DEMO_PREFIX)
        .values_list("phone", flat=True)
    )
    phones = [demo_phone(BULK_OFFSET + i) for i in range(count)]
    phones = [p for p in phones if p not in existing]

    with transaction.atomic():
        users = User.objects.bulk_create([
            User(phone=phone, full_name="Load Test %s" % phone[-5:],
                 password=unusable, active_role=User.Role.PROVIDER,
                 phone_verified=rng.random() < 0.8)
            for phone in phones
        ], batch_size=500)
        profiles = ProviderProfile.objects.bulk_create([
            ProviderProfile(
                user=user, display_name=user.full_name,
                experience_years=rng.randint(0, 20),
                identity_verified=rng.random() < 0.5,
                skill_verified=rng.random() < 0.25,
                jobs_completed=(done := rng.randint(0, 150)),
                jobs_accepted=done + (extra := rng.randint(0, 20)),
                jobs_cancelled=rng.randint(0, extra),
                requests_received=done + extra + rng.randint(0, 30),
                median_response_seconds=rng.randint(60, 8 * 3600),
            )
            for user in users
        ], batch_size=500)

        offerings, areas, windows = [], [], []
        for profile in profiles:
            for service in rng.sample(services, rng.randint(1, 4)):
                offerings.append(ProviderService(
                    provider=profile, service=service,
                    price=_price_for(service, rng)))
            for thana in rng.sample(thanas, rng.randint(1, 3)):
                areas.append(ServiceArea(provider=profile, location=thana))
            for day in rng.sample(range(7), rng.randint(3, 7)):
                windows.append(Availability(provider=profile, weekday=day,
                                            start_time=time(9), end_time=time(18)))
        ProviderService.objects.bulk_create(offerings, batch_size=1000)
        ServiceArea.objects.bulk_create(areas, batch_size=1000)
        Availability.objects.bulk_create(windows, batch_size=1000)

    log("  bulk: %d providers, %d offerings, %d service areas"
        % (len(profiles), len(offerings), len(areas)))
    return len(profiles)


def reset_demo():
    users = User.objects.filter(phone__startswith=DEMO_PREFIX)
    with transaction.atomic():
        LedgerEntry.objects.filter(provider__user__in=users).delete()
        Payment.objects.filter(provider__user__in=users).delete()
        bookings = Booking.objects.filter(provider__user__in=users) | \
            Booking.objects.filter(customer__user__in=users)
        ids = list(bookings.values_list("pk", flat=True))
        CustomerRating.objects.filter(booking_id__in=ids).delete()
        Review.objects.filter(booking_id__in=ids).delete()
        Booking.objects.filter(pk__in=ids).delete()
        ServiceRequest.objects.filter(customer__user__in=users).delete()
        removed = users.count()
        users.delete()
    return removed
