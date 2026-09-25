from django.db.models import Prefetch

from .models import Booking, BookingEvent, ProviderResponse, ServiceRequest


def requests_for_customer(customer_id, *, state=None):
    qs = (
        ServiceRequest.objects
        .filter(customer_id=customer_id)
        .select_related("service", "service__category", "location",
                        "target_provider")
        .prefetch_related("responses")
    )
    if state:
        qs = qs.filter(state=state)
    return qs


def open_requests_for_provider(provider):
    responded = ProviderResponse.objects.filter(
        provider=provider,
    ).values("request_id")

    return (
        ServiceRequest.objects
        .filter(state=ServiceRequest.State.OPEN)
        .exclude(pk__in=responded)
        .select_related("service", "service__category", "location")
        .prefetch_related("responses")
        .order_by("-created_at")
    )


def bookings_for(*, customer_id=None, provider_id=None, state=None):
    qs = (
        Booking.objects
        .select_related("provider", "customer", "request",
                        "request__service", "request__service__category",
                        "request__location")
    )
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    if provider_id is not None:
        qs = qs.filter(provider_id=provider_id)
    if state:
        qs = qs.filter(state=state)
    return qs


def booking_detail(booking_id, *, customer_id=None, provider_id=None):
    qs = (
        Booking.objects
        .select_related("provider", "customer", "customer__user", "request",
                        "request__service", "request__service__category",
                        "request__location")
        .prefetch_related(
            Prefetch("events",
                     queryset=BookingEvent.objects.order_by("created_at"))
        )
    )
    if customer_id is not None:
        qs = qs.filter(customer_id=customer_id)
    if provider_id is not None:
        qs = qs.filter(provider_id=provider_id)
    return qs.filter(pk=booking_id).first()
