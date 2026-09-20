"""Service-layer tests: registration, OTP issue/verify, roles."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts import services
from apps.accounts.models import CustomerProfile, PhoneOTP, ProviderProfile
from apps.common.exceptions import DomainError, RateLimited, VerificationError

User = get_user_model()
pytestmark = pytest.mark.django_db

PHONE = "+8801712345678"


# ---------------------------------------------------------------- registration
def test_register_creates_user_and_customer_profile():
    user = services.register_user(
        phone=PHONE, password="testpass123", full_name="Rumana A.",
    )
    assert user.phone == PHONE
    assert CustomerProfile.objects.filter(user=user).exists()
    assert user.roles == [User.Role.CUSTOMER]


def test_register_as_provider_creates_provider_profile():
    user = services.register_user(
        phone=PHONE, password="testpass123", full_name="Kamal H.",
        role=User.Role.PROVIDER,
    )
    profile = ProviderProfile.objects.get(user=user)
    assert profile.display_name == "Kamal H."
    assert profile.trust_score == 0
    assert profile.trust_tier == ProviderProfile.Tier.NEW


def test_register_normalises_phone_before_storing():
    user = services.register_user(phone="01712345678", password="testpass123")
    assert user.phone == PHONE


def test_register_rejects_duplicate_phone_in_any_format():
    services.register_user(phone=PHONE, password="testpass123")
    with pytest.raises(DomainError) as exc:
        services.register_user(phone="01712345678", password="other123")
    assert exc.value.code == "phone_taken"


def test_register_requires_an_identifier():
    with pytest.raises(DomainError) as exc:
        services.register_user(password="testpass123")
    assert exc.value.code == "identifier_required"


def test_register_with_email_only_is_allowed():
    user = services.register_user(email="R@Example.COM",
                                  password="testpass123")
    assert user.email == "r@example.com"
    assert user.phone is None


def test_password_is_hashed_not_stored_plain():
    user = services.register_user(phone=PHONE, password="testpass123")
    assert user.password != "testpass123"
    assert user.check_password("testpass123")


# ------------------------------------------------------------------------ otp
def test_send_otp_creates_usable_row_without_exposing_code():
    otp = services.send_phone_otp(phone=PHONE)
    assert otp.is_usable
    assert otp.expires_at > timezone.now()
    # The plaintext code must never be persisted.
    assert not hasattr(otp, "code")
    assert len(otp.code_hash) == 64


def test_verify_marks_phone_verified(monkeypatch):
    user = services.register_user(phone=PHONE, password="testpass123")
    assert user.phone_verified is False

    code = _issue_known_code(monkeypatch, PHONE)
    returned = services.verify_phone_otp(phone=PHONE, code=code)

    assert returned.id == user.id
    user.refresh_from_db()
    assert user.phone_verified is True


def test_verify_accepts_any_input_format(monkeypatch):
    services.register_user(phone=PHONE, password="testpass123")
    code = _issue_known_code(monkeypatch, PHONE)
    # User types the local format on the verify screen.
    services.verify_phone_otp(phone="01712345678", code=code)
    assert User.objects.get(phone=PHONE).phone_verified is True


def test_wrong_code_increments_attempts_and_does_not_verify(monkeypatch):
    services.register_user(phone=PHONE, password="testpass123")
    _issue_known_code(monkeypatch, PHONE)

    with pytest.raises(VerificationError) as exc:
        services.verify_phone_otp(phone=PHONE, code="000000")

    assert exc.value.code == "otp_mismatch"
    assert PhoneOTP.objects.get(phone=PHONE).attempts == 1
    assert User.objects.get(phone=PHONE).phone_verified is False


def test_code_cannot_be_reused(monkeypatch):
    services.register_user(phone=PHONE, password="testpass123")
    code = _issue_known_code(monkeypatch, PHONE)

    services.verify_phone_otp(phone=PHONE, code=code)
    with pytest.raises(VerificationError) as exc:
        services.verify_phone_otp(phone=PHONE, code=code)
    assert exc.value.code == "otp_not_found"


def test_expired_code_is_rejected(monkeypatch):
    services.register_user(phone=PHONE, password="testpass123")
    code = _issue_known_code(monkeypatch, PHONE)

    otp = PhoneOTP.objects.get(phone=PHONE)
    otp.expires_at = timezone.now() - timezone.timedelta(seconds=1)
    otp.save(update_fields=["expires_at"])

    with pytest.raises(VerificationError) as exc:
        services.verify_phone_otp(phone=PHONE, code=code)
    assert exc.value.code == "otp_expired"


def test_send_is_rate_limited_per_hour():
    for _ in range(settings.OTP_MAX_SENDS_PER_HOUR):
        services.send_phone_otp(phone=PHONE)
    with pytest.raises(RateLimited):
        services.send_phone_otp(phone=PHONE)


def test_new_code_supersedes_the_previous_one(monkeypatch):
    services.register_user(phone=PHONE, password="testpass123")
    first = _issue_known_code(monkeypatch, PHONE)
    second = _issue_known_code(monkeypatch, PHONE, code="654321")

    assert first != second
    with pytest.raises(VerificationError):
        services.verify_phone_otp(phone=PHONE, code=first)
    services.verify_phone_otp(phone=PHONE, code=second)


def test_too_many_wrong_attempts_locks_the_code(monkeypatch):
    services.register_user(phone=PHONE, password="testpass123")
    code = _issue_known_code(monkeypatch, PHONE)

    for _ in range(settings.OTP_MAX_VERIFY_ATTEMPTS):
        with pytest.raises(VerificationError):
            services.verify_phone_otp(phone=PHONE, code="000000")

    # Even the correct code is refused once the attempt budget is spent.
    with pytest.raises(RateLimited):
        services.verify_phone_otp(phone=PHONE, code=code)


def test_purge_removes_only_old_rows():
    services.send_phone_otp(phone=PHONE)
    old = PhoneOTP.objects.create(
        phone="+8801812345678", code_hash="x" * 64,
        expires_at=timezone.now(),
    )
    PhoneOTP.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timezone.timedelta(hours=48)
    )

    deleted = services.purge_expired_otps(older_than_hours=24)
    assert deleted == 1
    assert PhoneOTP.objects.filter(phone=PHONE).exists()


def test_purge_is_idempotent():
    services.purge_expired_otps()
    assert services.purge_expired_otps() == 0


# ---------------------------------------------------------------------- roles
def test_user_can_hold_both_roles():
    user = services.register_user(phone=PHONE, password="testpass123")
    services.create_profile(user_id=user.id, role=User.Role.PROVIDER)

    user.refresh_from_db()
    assert set(user.roles) == {User.Role.CUSTOMER, User.Role.PROVIDER}


def test_create_profile_is_idempotent():
    user = services.register_user(phone=PHONE, password="testpass123")
    first = services.create_profile(user_id=user.id, role=User.Role.PROVIDER)
    second = services.create_profile(user_id=user.id, role=User.Role.PROVIDER)
    assert first.pk == second.pk


def test_switch_role_requires_holding_that_role():
    user = services.register_user(phone=PHONE, password="testpass123")
    with pytest.raises(DomainError) as exc:
        services.switch_active_role(user_id=user.id, role=User.Role.PROVIDER)
    assert exc.value.code == "role_not_held"


def test_switch_role_succeeds_when_profile_exists():
    user = services.register_user(phone=PHONE, password="testpass123")
    services.create_profile(user_id=user.id, role=User.Role.PROVIDER)

    updated = services.switch_active_role(user_id=user.id,
                                          role=User.Role.PROVIDER)
    assert updated.active_role == User.Role.PROVIDER


# -------------------------------------------------------------------- helpers
def _issue_known_code(monkeypatch, phone, code="123456"):
    """
    Issue an OTP whose plaintext we know.

    The service never returns the code, which is correct -- so tests pin the
    generator rather than reaching into internals.
    """
    monkeypatch.setattr(PhoneOTP, "generate_code", staticmethod(lambda: code))
    services.send_phone_otp(phone=phone)
    return code
