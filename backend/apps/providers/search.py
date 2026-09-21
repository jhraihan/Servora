from decimal import Decimal

from django.db.models import (
    DecimalField, Exists, F, Min, OuterRef, Prefetch, Q, Value,
)
from django.db.models.functions import Coalesce

from apps.accounts.models import ProviderProfile
from apps.catalogue.models import Location

from .models import (
    Availability, AvailabilityException, ProviderService, ServiceArea,
)

SORT_TRUST = "-trust_score"
SORT_PRICE = "price"
SORT_DISTANCE = "distance"
SORT_CHOICES = (SORT_TRUST, SORT_PRICE, SORT_DISTANCE)

EARTH_MILES_PER_DEGREE = 69.0


def search_providers(*, service_id=None, category_slug=None, location_id=None,
                     min_trust=None, tier=None, verified_only=False,
                     price_min=None, price_max=None, available_on=None,
                     ordering=SORT_TRUST):
    queryset = (
        ProviderProfile.objects
        .filter(is_accepting_work=True, user__is_active=True,
                user__suspended_at__isnull=True)
        .exclude(trust_tier=ProviderProfile.Tier.UNDER_REVIEW)
        .select_related("user")
        .prefetch_related(
            Prefetch(
                "service_areas",
                queryset=ServiceArea.objects.select_related(
                    "location", "location__parent",
                ),
            )
        )
    )

    offerings = ProviderService.objects.filter(
        provider=OuterRef("pk"), is_active=True, service__is_active=True,
    )
    if service_id:
        offerings = offerings.filter(service_id=service_id)
    if category_slug:
        offerings = offerings.filter(service__category__slug=category_slug)
    if price_min is not None:
        offerings = offerings.filter(price__gte=price_min)
    if price_max is not None:
        offerings = offerings.filter(price__lte=price_max)

    if service_id or category_slug or price_min is not None \
            or price_max is not None:
        queryset = queryset.filter(Exists(offerings))

    queryset = queryset.annotate(
        matched_price=_matched_price_subquery(
            service_id, category_slug, price_min, price_max,
        )
    )

    if location_id:
        queryset = queryset.filter(
            service_areas__location_id__in=_expand_location(location_id)
        ).distinct()

    if min_trust is not None:
        queryset = queryset.filter(trust_score__gte=min_trust)

    if tier:
        queryset = queryset.filter(trust_tier=tier)

    if verified_only:
        queryset = queryset.filter(identity_verified=True)

    if available_on is not None:
        queryset = queryset.filter(_availability_filter(available_on))

    return _apply_ordering(queryset, ordering, location_id)


def _matched_price_subquery(service_id, category_slug, price_min, price_max):
    from django.db.models import Subquery

    inner = ProviderService.objects.filter(
        provider=OuterRef("pk"), is_active=True, service__is_active=True,
    )
    if service_id:
        inner = inner.filter(service_id=service_id)
    if category_slug:
        inner = inner.filter(service__category__slug=category_slug)
    if price_min is not None:
        inner = inner.filter(price__gte=price_min)
    if price_max is not None:
        inner = inner.filter(price__lte=price_max)

    return Subquery(
        inner.values("provider").annotate(lowest=Min("price")).values("lowest"),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )


def _expand_location(location_id):
    location = Location.objects.filter(pk=location_id).first()
    if location is None:
        return []
    return location.descendant_ids() + _ancestor_ids(location)


def _ancestor_ids(location):
    return [node.pk for node in location.ancestors()
            if node.level != Location.Level.CITY]


def _availability_filter(on_date):
    weekday = on_date.weekday()

    weekly = Availability.objects.filter(
        provider=OuterRef("pk"), weekday=weekday,
    )
    blocked = AvailabilityException.objects.filter(
        provider=OuterRef("pk"), date=on_date, is_available=False,
    )
    extra = AvailabilityException.objects.filter(
        provider=OuterRef("pk"), date=on_date, is_available=True,
    )

    return (
        (Q(Exists(weekly)) & ~Q(Exists(blocked)))
        | Q(Exists(extra))
    )


def _apply_ordering(queryset, ordering, location_id):
    if ordering == SORT_PRICE:
        return queryset.order_by(
            Coalesce("matched_price", Value(Decimal("0"))).asc(),
            "-identity_verified", "-trust_score", "pk",
        )

    if ordering == SORT_DISTANCE and location_id:
        return _order_by_distance(queryset, location_id)

    return queryset.order_by("-trust_score", "-identity_verified", "pk")


def _order_by_distance(queryset, location_id):
    origin = Location.objects.filter(pk=location_id).first()
    if origin is None or not origin.has_coordinates:
        return queryset.order_by("-trust_score", "-identity_verified", "pk")

    return queryset.annotate(
        distance=Min(
            _squared_degree_distance(origin)
        )
    ).order_by("distance", "-trust_score", "pk")


def _squared_degree_distance(origin):
    from django.db.models.functions import Abs

    lat = F("service_areas__location__latitude")
    lon = F("service_areas__location__longitude")
    return Abs(lat - Value(origin.latitude)) + Abs(
        lon - Value(origin.longitude)
    )
