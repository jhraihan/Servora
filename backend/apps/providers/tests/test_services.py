from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.common.exceptions import DomainError, NotFound
from apps.providers import services
from apps.providers.models import (
    Availability, AvailabilityException, ProviderService, ServiceArea,
    VerificationDocument, WorkPhoto,
)

pytestmark = pytest.mark.django_db


def test_update_profile_changes_editable_fields(provider):
    updated = services.update_profile(
        provider_id=provider.id, display_name="Kamal AC Services",
        experience_years=14,
    )
    assert updated.display_name == "Kamal AC Services"
    assert updated.experience_years == 14


def test_update_profile_rejects_trust_fields(provider):
    with pytest.raises(DomainError) as exc:
        services.update_profile(provider_id=provider.id, trust_score=99)
    assert exc.value.code == "field_not_editable"
    provider.refresh_from_db()
    assert provider.trust_score == 0


def test_update_profile_rejects_verification_fields(provider):
    with pytest.raises(DomainError):
        services.update_profile(provider_id=provider.id,
                                identity_verified=True)
    provider.refresh_from_db()
    assert provider.identity_verified is False


def test_accepting_work_toggle(provider):
    services.set_accepting_work(provider_id=provider.id, accepting=False)
    provider.refresh_from_db()
    assert provider.is_accepting_work is False

    services.set_accepting_work(provider_id=provider.id, accepting=True)
    provider.refresh_from_db()
    assert provider.is_accepting_work is True


def test_add_offering_uses_service_default_duration(provider, service):
    offering = services.add_offering(
        provider_id=provider.id, service_id=service.id,
        price=Decimal("1800"),
    )
    assert offering.estimated_duration_minutes == 90


def test_add_offering_rejects_duplicate_service(provider, service):
    services.add_offering(provider_id=provider.id, service_id=service.id,
                          price=Decimal("1800"))
    with pytest.raises(DomainError) as exc:
        services.add_offering(provider_id=provider.id, service_id=service.id,
                              price=Decimal("2000"))
    assert exc.value.code == "offering_exists"


def test_add_offering_rejects_unknown_service(provider):
    with pytest.raises(NotFound) as exc:
        services.add_offering(provider_id=provider.id, service_id=99999,
                              price=Decimal("500"))
    assert exc.value.code == "service_not_found"


def test_offering_price_flag_reflects_band(provider, service):
    low = services.add_offering(provider_id=provider.id,
                                service_id=service.id, price=Decimal("800"))
    assert low.price_flag == "low"

    services.update_offering(provider_id=provider.id, offering_id=low.id,
                             price=Decimal("1800"))
    low.refresh_from_db()
    assert low.price_flag == "normal"


def test_update_offering_rejects_foreign_offering(provider, other_provider,
                                                  service):
    offering = services.add_offering(provider_id=other_provider.id,
                                     service_id=service.id,
                                     price=Decimal("1800"))
    with pytest.raises(NotFound):
        services.update_offering(provider_id=provider.id,
                                 offering_id=offering.id,
                                 price=Decimal("1"))


def test_remove_offering_rejects_foreign_offering(provider, other_provider,
                                                  service):
    offering = services.add_offering(provider_id=other_provider.id,
                                     service_id=service.id,
                                     price=Decimal("1800"))
    with pytest.raises(NotFound):
        services.remove_offering(provider_id=provider.id,
                                 offering_id=offering.id)
    assert ProviderService.objects.filter(pk=offering.id).exists()


def test_set_service_areas_replaces_previous(provider, dhanmondi, gulshan):
    services.set_service_areas(provider_id=provider.id,
                               location_ids=[dhanmondi.id])
    services.set_service_areas(provider_id=provider.id,
                               location_ids=[gulshan.id])

    areas = ServiceArea.objects.filter(provider=provider)
    assert [a.location_id for a in areas] == [gulshan.id]


def test_set_service_areas_rejects_city_level(provider, dhaka):
    with pytest.raises(DomainError) as exc:
        services.set_service_areas(provider_id=provider.id,
                                   location_ids=[dhaka.id])
    assert exc.value.code == "location_too_broad"


def test_set_service_areas_rejects_unknown_location(provider):
    with pytest.raises(DomainError) as exc:
        services.set_service_areas(provider_id=provider.id,
                                   location_ids=[99999])
    assert exc.value.code == "invalid_location"


def test_set_service_areas_records_surcharge(provider, dhanmondi):
    services.set_service_areas(
        provider_id=provider.id, location_ids=[dhanmondi.id],
        surcharges={str(dhanmondi.id): Decimal("150")},
    )
    area = ServiceArea.objects.get(provider=provider)
    assert area.travel_surcharge == Decimal("150")


def test_set_weekly_availability_stores_windows(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 0, "start_time": time(9, 0), "end_time": time(13, 0)},
        {"weekday": 0, "start_time": time(14, 0), "end_time": time(18, 0)},
        {"weekday": 2, "start_time": time(9, 0), "end_time": time(17, 0)},
    ])
    assert Availability.objects.filter(provider=provider).count() == 3


def test_weekly_availability_rejects_overlap(provider):
    with pytest.raises(DomainError) as exc:
        services.set_weekly_availability(provider_id=provider.id, windows=[
            {"weekday": 0, "start_time": time(9, 0), "end_time": time(13, 0)},
            {"weekday": 0, "start_time": time(12, 0), "end_time": time(16, 0)},
        ])
    assert exc.value.code == "overlapping_windows"


def test_weekly_availability_allows_same_times_on_different_days(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 0, "start_time": time(9, 0), "end_time": time(13, 0)},
        {"weekday": 1, "start_time": time(9, 0), "end_time": time(13, 0)},
    ])
    assert Availability.objects.filter(provider=provider).count() == 2


def test_weekly_availability_rejects_backwards_window(provider):
    with pytest.raises(DomainError) as exc:
        services.set_weekly_availability(provider_id=provider.id, windows=[
            {"weekday": 0, "start_time": time(17, 0), "end_time": time(9, 0)},
        ])
    assert exc.value.code == "invalid_window"


def test_weekly_availability_replaces_previous(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 0, "start_time": time(9, 0), "end_time": time(13, 0)},
    ])
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 3, "start_time": time(10, 0), "end_time": time(14, 0)},
    ])
    remaining = Availability.objects.filter(provider=provider)
    assert [w.weekday for w in remaining] == [3]


def test_resolve_availability_uses_weekly_pattern(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 0, "start_time": time(9, 0), "end_time": time(17, 0)},
    ])
    monday = _next_weekday(0)
    assert services.resolve_availability(provider_id=provider.id,
                                         date=monday) == [
        (time(9, 0), time(17, 0))
    ]


def test_resolve_availability_empty_on_unscheduled_day(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 0, "start_time": time(9, 0), "end_time": time(17, 0)},
    ])
    tuesday = _next_weekday(1)
    assert services.resolve_availability(provider_id=provider.id,
                                         date=tuesday) == []


def test_leave_exception_overrides_weekly_pattern(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": 0, "start_time": time(9, 0), "end_time": time(17, 0)},
    ])
    monday = _next_weekday(0)
    services.set_availability_exception(
        provider_id=provider.id, date=monday, is_available=False,
        reason="Family event",
    )
    assert services.resolve_availability(provider_id=provider.id,
                                         date=monday) == []


def test_extra_day_exception_adds_availability(provider):
    friday = _next_weekday(4)
    services.set_availability_exception(
        provider_id=provider.id, date=friday, is_available=True,
        start_time=time(10, 0), end_time=time(14, 0),
    )
    assert services.resolve_availability(provider_id=provider.id,
                                         date=friday) == [
        (time(10, 0), time(14, 0))
    ]


def test_available_exception_requires_hours(provider):
    with pytest.raises(DomainError) as exc:
        services.set_availability_exception(
            provider_id=provider.id, date=date.today(), is_available=True,
        )
    assert exc.value.code == "hours_required"


def test_exception_is_updated_not_duplicated(provider):
    day = _next_weekday(0)
    services.set_availability_exception(provider_id=provider.id, date=day,
                                        is_available=False)
    services.set_availability_exception(
        provider_id=provider.id, date=day, is_available=True,
        start_time=time(9, 0), end_time=time(12, 0),
    )
    assert AvailabilityException.objects.filter(provider=provider,
                                                date=day).count() == 1


def test_availability_calendar_spans_requested_days(provider):
    services.set_weekly_availability(provider_id=provider.id, windows=[
        {"weekday": d, "start_time": time(9, 0), "end_time": time(17, 0)}
        for d in range(7)
    ])
    calendar = services.availability_calendar(
        provider_id=provider.id, start_date=date.today(), days=7,
    )
    assert len(calendar) == 7
    assert all(len(w) == 1 for w in calendar.values())


def test_verification_upload_supersedes_pending(provider):
    services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("first.jpg"),
    )
    services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("second.jpg"),
    )
    pending = VerificationDocument.objects.filter(
        provider=provider, document_type="nid_front", status="pending",
    )
    assert pending.count() == 1


def test_approving_both_nid_sides_sets_identity_verified(provider, admin_user):
    front = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("front.jpg"),
    )
    back = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_back",
        file=_fake_file("back.jpg"),
    )

    services.decide_verification(document_id=front.id,
                                 reviewer_id=admin_user.id, approve=True)
    provider.refresh_from_db()
    assert provider.identity_verified is False

    services.decide_verification(document_id=back.id,
                                 reviewer_id=admin_user.id, approve=True)
    provider.refresh_from_db()
    assert provider.identity_verified is True


def test_trade_certificate_sets_skill_verified(provider, admin_user):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="trade_certificate",
        file=_fake_file("cert.pdf"),
    )
    services.decide_verification(document_id=doc.id,
                                 reviewer_id=admin_user.id, approve=True)
    provider.refresh_from_db()
    assert provider.skill_verified is True


def test_rejection_requires_reason(provider, admin_user):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("front.jpg"),
    )
    with pytest.raises(DomainError) as exc:
        services.decide_verification(document_id=doc.id,
                                     reviewer_id=admin_user.id, approve=False)
    assert exc.value.code == "reason_required"


def test_rejection_leaves_provider_unverified(provider, admin_user):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("front.jpg"),
    )
    services.decide_verification(document_id=doc.id,
                                 reviewer_id=admin_user.id, approve=False,
                                 rejection_reason="Image is unreadable")
    provider.refresh_from_db()
    assert provider.identity_verified is False
    doc.refresh_from_db()
    assert doc.rejection_reason == "Image is unreadable"


def test_document_cannot_be_reviewed_twice(provider, admin_user):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("front.jpg"),
    )
    services.decide_verification(document_id=doc.id,
                                 reviewer_id=admin_user.id, approve=True)
    with pytest.raises(DomainError) as exc:
        services.decide_verification(document_id=doc.id,
                                     reviewer_id=admin_user.id, approve=True)
    assert exc.value.code == "already_reviewed"


def test_decision_sets_purge_deadline(provider, admin_user):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("front.jpg"),
    )
    services.decide_verification(document_id=doc.id,
                                 reviewer_id=admin_user.id, approve=True)
    doc.refresh_from_db()
    expected = timezone.now() + timedelta(
        days=services.VERIFICATION_RETENTION_DAYS
    )
    assert abs((doc.purge_after - expected).total_seconds()) < 60


def test_purge_removes_only_expired_files(provider, admin_user):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("front.jpg"),
    )
    services.decide_verification(document_id=doc.id,
                                 reviewer_id=admin_user.id, approve=True)

    assert services.purge_reviewed_documents() == 0

    doc.refresh_from_db()
    doc.purge_after = timezone.now() - timedelta(days=1)
    doc.save(update_fields=["purge_after"])

    assert services.purge_reviewed_documents() == 1
    doc.refresh_from_db()
    assert not doc.file


def test_purge_is_idempotent(provider):
    assert services.purge_reviewed_documents() == 0
    assert services.purge_reviewed_documents() == 0


def test_work_photo_limit_enforced(provider):
    for _ in range(WorkPhoto.MAX_PER_PROVIDER):
        services.add_work_photo(provider_id=provider.id,
                                image=_fake_image())

    with pytest.raises(DomainError) as exc:
        services.add_work_photo(provider_id=provider.id, image=_fake_image())
    assert exc.value.code == "photo_limit_reached"


def test_remove_work_photo_rejects_foreign_photo(provider, other_provider):
    photo = services.add_work_photo(provider_id=other_provider.id,
                                    image=_fake_image())
    with pytest.raises(NotFound):
        services.remove_work_photo(provider_id=provider.id,
                                   photo_id=photo.id)


def _next_weekday(weekday):
    today = date.today()
    offset = (weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=offset)


def _fake_file(name="doc.jpg"):
    return SimpleUploadedFile(name, b"fake-bytes", content_type="image/jpeg")


def _fake_image(name="photo.png"):
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
        b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9c"
        b"c\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`"
        b"\x82"
    )
    return SimpleUploadedFile(name, png, content_type="image/png")


def test_verification_files_stored_outside_public_media(provider, settings):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("nid.jpg"),
    )
    stored = Path(doc.file.path).resolve()

    assert stored.is_relative_to(Path(settings.PRIVATE_MEDIA_ROOT).resolve())
    assert not stored.is_relative_to(Path(settings.MEDIA_ROOT).resolve())


def test_verification_file_has_no_public_url(provider):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("nid.jpg"),
    )
    with pytest.raises(NotImplementedError):
        doc.file.url


def test_work_photos_remain_in_public_media(provider, settings):
    photo = services.add_work_photo(provider_id=provider.id,
                                    image=_fake_image())
    stored = Path(photo.image.path).resolve()
    assert stored.is_relative_to(Path(settings.MEDIA_ROOT).resolve())


def test_verification_filename_is_not_guessable(provider):
    doc = services.submit_verification_document(
        provider_id=provider.id, document_type="nid_front",
        file=_fake_file("kamal-nid-front.jpg"),
    )
    assert "kamal" not in doc.file.name
    assert len(Path(doc.file.name).stem) == 32
