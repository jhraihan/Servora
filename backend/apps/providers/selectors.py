from django.db.models import Prefetch

from apps.accounts.models import ProviderProfile

from .models import (
    Availability, ProviderService, ServiceArea, VerificationDocument,
    WorkPhoto,
)


def provider_detail(provider_id):
    return (
        ProviderProfile.objects
        .select_related("user")
        .prefetch_related(
            Prefetch(
                "offerings",
                queryset=ProviderService.objects
                .filter(is_active=True)
                .select_related("service", "service__category"),
            ),
            Prefetch(
                "service_areas",
                queryset=ServiceArea.objects.select_related("location"),
            ),
            Prefetch("availability",
                     queryset=Availability.objects.order_by("weekday",
                                                            "start_time")),
            Prefetch("work_photos",
                     queryset=WorkPhoto.objects.order_by("display_order")),
        )
        .filter(pk=provider_id)
        .first()
    )


def offerings_for(provider_id, *, active_only=False):
    qs = (
        ProviderService.objects
        .filter(provider_id=provider_id)
        .select_related("service", "service__category")
    )
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def service_areas_for(provider_id):
    return (
        ServiceArea.objects
        .filter(provider_id=provider_id)
        .select_related("location", "location__parent")
    )


def weekly_availability_for(provider_id):
    return Availability.objects.filter(provider_id=provider_id)


def verification_documents_for(provider_id):
    return VerificationDocument.objects.filter(provider_id=provider_id)


def pending_verification_queue():
    return (
        VerificationDocument.objects
        .filter(status=VerificationDocument.Status.PENDING)
        .select_related("provider", "provider__user")
        .order_by("created_at")
    )
