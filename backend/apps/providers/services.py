import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import ProviderProfile
from apps.catalogue.models import Location, Service
from apps.common.exceptions import DomainError, NotFound

from .models import (
    Availability, AvailabilityException, ProviderService, ServiceArea,
    VerificationDocument, WorkPhoto,
)

logger = logging.getLogger(__name__)

VERIFICATION_RETENTION_DAYS = 90


def _get_provider(provider_id):
    provider = ProviderProfile.objects.filter(pk=provider_id).first()
    if provider is None:
        raise NotFound("No such provider.", code="provider_not_found")
    return provider


@transaction.atomic
def update_profile(*, provider_id, **fields):
    provider = ProviderProfile.objects.select_for_update().get(pk=provider_id)

    editable = {"display_name", "bio", "experience_years",
                "is_accepting_work"}
    unknown = set(fields) - editable
    if unknown:
        raise DomainError(
            "These fields cannot be edited here: %s" % ", ".join(sorted(unknown)),
            code="field_not_editable",
        )

    for name, value in fields.items():
        setattr(provider, name, value)
    provider.save(update_fields=list(fields) + ["updated_at"])
    return provider


@transaction.atomic
def set_accepting_work(*, provider_id, accepting):
    provider = ProviderProfile.objects.select_for_update().get(pk=provider_id)
    provider.is_accepting_work = accepting
    provider.save(update_fields=["is_accepting_work", "updated_at"])
    logger.info("Provider %s accepting_work=%s", provider_id, accepting)
    return provider


@transaction.atomic
def add_offering(*, provider_id, service_id, price, duration_minutes=None,
                 notes=""):
    provider = _get_provider(provider_id)

    service = Service.objects.filter(pk=service_id, is_active=True).first()
    if service is None:
        raise NotFound("No such service.", code="service_not_found")

    if price < 0:
        raise DomainError("Price cannot be negative.", code="invalid_price")

    if ProviderService.objects.filter(provider=provider,
                                      service=service).exists():
        raise DomainError(
            "You already offer this service. Edit the existing entry instead.",
            code="offering_exists",
        )

    offering = ProviderService.objects.create(
        provider=provider,
        service=service,
        price=price,
        estimated_duration_minutes=(
            duration_minutes or service.typical_duration_minutes
        ),
        notes=notes,
    )
    return offering


@transaction.atomic
def update_offering(*, provider_id, offering_id, **fields):
    offering = (
        ProviderService.objects
        .select_for_update()
        .filter(pk=offering_id, provider_id=provider_id)
        .first()
    )
    if offering is None:
        raise NotFound("No such offering.", code="offering_not_found")

    editable = {"price", "estimated_duration_minutes", "notes", "is_active"}
    unknown = set(fields) - editable
    if unknown:
        raise DomainError(
            "These fields cannot be edited: %s" % ", ".join(sorted(unknown)),
            code="field_not_editable",
        )

    if "price" in fields and fields["price"] < 0:
        raise DomainError("Price cannot be negative.", code="invalid_price")

    for name, value in fields.items():
        setattr(offering, name, value)
    offering.save(update_fields=list(fields) + ["updated_at"])
    return offering


@transaction.atomic
def remove_offering(*, provider_id, offering_id):
    offering = (
        ProviderService.objects
        .filter(pk=offering_id, provider_id=provider_id)
        .first()
    )
    if offering is None:
        raise NotFound("No such offering.", code="offering_not_found")
    offering.delete()


@transaction.atomic
def set_service_areas(*, provider_id, location_ids, surcharges=None):
    provider = _get_provider(provider_id)
    surcharges = surcharges or {}

    locations = list(
        Location.objects.filter(pk__in=location_ids, is_active=True)
    )
    if len(locations) != len(set(location_ids)):
        raise DomainError("One or more locations do not exist.",
                          code="invalid_location")

    for location in locations:
        if location.level == Location.Level.CITY:
            raise DomainError(
                "Service areas must be a thana or an area, not a whole city.",
                code="location_too_broad",
            )

    ServiceArea.objects.filter(provider=provider).delete()
    created = [
        ServiceArea.objects.create(
            provider=provider,
            location=location,
            travel_surcharge=surcharges.get(str(location.pk), 0),
        )
        for location in locations
    ]
    return created


@transaction.atomic
def set_weekly_availability(*, provider_id, windows):
    provider = _get_provider(provider_id)

    by_day = {}
    for window in windows:
        weekday = window["weekday"]
        start, end = window["start_time"], window["end_time"]

        if end <= start:
            raise DomainError(
                "A window must end after it starts.",
                code="invalid_window",
                details={"weekday": weekday},
            )

        for existing_start, existing_end in by_day.get(weekday, []):
            if start < existing_end and existing_start < end:
                raise DomainError(
                    "Two windows on the same day overlap.",
                    code="overlapping_windows",
                    details={"weekday": weekday},
                )
        by_day.setdefault(weekday, []).append((start, end))

    Availability.objects.filter(provider=provider).delete()
    created = [
        Availability.objects.create(
            provider=provider,
            weekday=window["weekday"],
            start_time=window["start_time"],
            end_time=window["end_time"],
        )
        for window in windows
    ]
    return created


@transaction.atomic
def set_availability_exception(*, provider_id, date, is_available,
                               start_time=None, end_time=None, reason=""):
    provider = _get_provider(provider_id)

    if is_available and (start_time is None or end_time is None):
        raise DomainError(
            "An available-day exception needs a start and end time.",
            code="hours_required",
        )
    if is_available and end_time <= start_time:
        raise DomainError("A window must end after it starts.",
                          code="invalid_window")

    exception, _created = AvailabilityException.objects.update_or_create(
        provider=provider,
        date=date,
        defaults={
            "is_available": is_available,
            "start_time": start_time if is_available else None,
            "end_time": end_time if is_available else None,
            "reason": reason,
        },
    )
    return exception


def resolve_availability(*, provider_id, date):
    provider = _get_provider(provider_id)

    exception = AvailabilityException.objects.filter(
        provider=provider, date=date
    ).first()

    if exception is not None:
        if not exception.is_available:
            return []
        return [(exception.start_time, exception.end_time)]

    windows = Availability.objects.filter(
        provider=provider, weekday=date.weekday()
    ).order_by("start_time")
    return [(w.start_time, w.end_time) for w in windows]


def availability_calendar(*, provider_id, start_date, days=14):
    return {
        (start_date + timedelta(days=offset)): resolve_availability(
            provider_id=provider_id,
            date=start_date + timedelta(days=offset),
        )
        for offset in range(days)
    }


@transaction.atomic
def submit_verification_document(*, provider_id, document_type, file):
    provider = _get_provider(provider_id)

    VerificationDocument.objects.filter(
        provider=provider,
        document_type=document_type,
        status=VerificationDocument.Status.PENDING,
    ).delete()

    document = VerificationDocument.objects.create(
        provider=provider,
        document_type=document_type,
        file=file,
    )
    logger.info("Verification document %s submitted by provider %s",
                document_type, provider_id)
    return document


@transaction.atomic
def decide_verification(*, document_id, reviewer_id, approve,
                        rejection_reason=""):
    document = (
        VerificationDocument.objects
        .select_for_update()
        .select_related("provider")
        .filter(pk=document_id)
        .first()
    )
    if document is None:
        raise NotFound("No such document.", code="document_not_found")

    if document.is_reviewed:
        raise DomainError("This document has already been reviewed.",
                          code="already_reviewed")

    if not approve and not rejection_reason:
        raise DomainError("A rejection needs a reason.",
                          code="reason_required")

    document.status = (
        VerificationDocument.Status.APPROVED if approve
        else VerificationDocument.Status.REJECTED
    )
    document.reviewed_by_id = reviewer_id
    document.reviewed_at = timezone.now()
    document.rejection_reason = "" if approve else rejection_reason
    document.purge_after = timezone.now() + timedelta(
        days=VERIFICATION_RETENTION_DAYS
    )
    document.save(update_fields=[
        "status", "reviewed_by", "reviewed_at", "rejection_reason",
        "purge_after", "updated_at",
    ])

    _sync_verification_flags(document.provider_id)
    return document


def _sync_verification_flags(provider_id):
    provider = ProviderProfile.objects.select_for_update().get(pk=provider_id)

    approved = set(
        VerificationDocument.objects
        .filter(provider_id=provider_id,
                status=VerificationDocument.Status.APPROVED)
        .values_list("document_type", flat=True)
    )

    provider.identity_verified = {
        VerificationDocument.DocumentType.NID_FRONT,
        VerificationDocument.DocumentType.NID_BACK,
    }.issubset(approved)
    provider.skill_verified = (
        VerificationDocument.DocumentType.TRADE_CERTIFICATE in approved
    )
    provider.address_verified = (
        VerificationDocument.DocumentType.ADDRESS_PROOF in approved
    )
    provider.save(update_fields=[
        "identity_verified", "skill_verified", "address_verified",
        "updated_at",
    ])
    return provider


@transaction.atomic
def add_work_photo(*, provider_id, image, caption=""):
    provider = _get_provider(provider_id)

    count = WorkPhoto.objects.filter(provider=provider).count()
    if count >= WorkPhoto.MAX_PER_PROVIDER:
        raise DomainError(
            "A provider may upload at most %d work photos."
            % WorkPhoto.MAX_PER_PROVIDER,
            code="photo_limit_reached",
        )

    return WorkPhoto.objects.create(
        provider=provider, image=image, caption=caption,
        display_order=count,
    )


@transaction.atomic
def remove_work_photo(*, provider_id, photo_id):
    photo = WorkPhoto.objects.filter(pk=photo_id,
                                     provider_id=provider_id).first()
    if photo is None:
        raise NotFound("No such photo.", code="photo_not_found")
    photo.delete()


def purge_reviewed_documents(*, now=None):
    now = now or timezone.now()
    stale = VerificationDocument.objects.filter(
        purge_after__lte=now
    ).exclude(file="")

    purged = 0
    for document in stale:
        document.file.delete(save=False)
        document.purge_after = None
        document.save(update_fields=["file", "purge_after"])
        purged += 1
    return purged
