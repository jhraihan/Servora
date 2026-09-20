"""
Read queries for the catalogue.

Kept out of views so the same query can serve an endpoint, a management
command, and a test without duplication (PRD 8.2).
"""

from django.db.models import Count, Prefetch, Q

from .models import Location, Service, ServiceCategory


def active_categories(*, with_service_count=False):
    qs = ServiceCategory.objects.filter(is_active=True)
    if with_service_count:
        # annotate() adds a GROUP BY, which silently DISCARDS the model's
        # Meta.ordering -- the rows then come back in whatever order the
        # database happens to produce. Re-apply it explicitly.
        qs = qs.annotate(
            service_count=Count("services",
                                filter=Q(services__is_active=True))
        ).order_by("display_order", "name")
    return qs


def category_by_slug(slug):
    """Category plus its active services, in one query pair."""
    return (
        ServiceCategory.objects
        .filter(is_active=True, slug=slug)
        .prefetch_related(
            Prefetch("services",
                     queryset=Service.objects.filter(is_active=True))
        )
        .first()
    )


def active_services(*, category_slug=None, search=None):
    qs = (
        Service.objects
        .filter(is_active=True, category__is_active=True)
        .select_related("category")
    )
    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if search:
        qs = qs.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )
    return qs


def location_tree(*, level=None, parent_id=None):
    qs = Location.objects.filter(is_active=True).select_related("parent")
    if level:
        qs = qs.filter(level=level)
    if parent_id is not None:
        qs = qs.filter(parent_id=parent_id)
    return qs


def service_areas_for(location_id):
    """
    Location ids that should match a request in this location.

    Expands downward: a provider registered for a thana serves every area
    inside it. Used by provider search in M5.
    """
    location = Location.objects.filter(pk=location_id).first()
    if location is None:
        return []
    return location.descendant_ids()
