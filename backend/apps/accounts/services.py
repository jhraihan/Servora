"""
Account write operations.

Service-layer rules (PRD 8.5) -- these keep the later move to a task queue a
one-line change per call site, so they hold from the first commit:

  1. Functions take IDs and plain values, never model instances.
  2. Functions never touch `request`; the acting user and IP arrive as
     explicit arguments.
  3. Functions are idempotent where the operation allows it.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.common.exceptions import DomainError, RateLimited, VerificationError

from .models import CustomerProfile, PhoneOTP, ProviderProfile
from .validators import normalise_bd_phone

logger = logging.getLogger(__name__)
User = get_user_model()


# --------------------------------------------------------------- registration
@transaction.atomic
def register_user(*, phone=None, email=None, password, full_name="",
                  role=User.Role.CUSTOMER):
    """
    Create a user and their initial role profile.

    Returns the created User. Raises DomainError if the identifier is taken.
    """
    if not phone and not email:
        raise DomainError(
            "Provide a phone number or an email address.",
            code="identifier_required",
        )

    phone = normalise_bd_phone(phone) if phone else None
    email = email.lower().strip() if email else None

    if phone and User.objects.filter(phone=phone).exists():
        raise DomainError("That phone number is already registered.",
                          code="phone_taken")
    if email and User.objects.filter(email=email).exists():
        raise DomainError("That email address is already registered.",
                          code="email_taken")

    user = User.objects.create_user(
        phone=phone, email=email, password=password, full_name=full_name,
        active_role=role,
    )
    create_profile(user_id=user.id, role=role)
    logger.info("Registered user %s as %s", user.id, role)
    return user


@transaction.atomic
def create_profile(*, user_id, role):
    """
    Attach a role profile to an existing user.

    Idempotent: creating a profile that already exists is a no-op, so a
    retried request cannot raise.
    """
    user = User.objects.select_for_update().get(pk=user_id)

    if role == User.Role.CUSTOMER:
        profile, _created = CustomerProfile.objects.get_or_create(user=user)
        return profile

    if role == User.Role.PROVIDER:
        profile, _created = ProviderProfile.objects.get_or_create(
            user=user,
            defaults={"display_name": user.full_name or "New provider"},
        )
        return profile

    raise DomainError("Unknown role.", code="unknown_role")


@transaction.atomic
def switch_active_role(*, user_id, role):
    """Change the UI role context. The user must already hold that role."""
    user = User.objects.select_for_update().get(pk=user_id)

    if role not in user.roles:
        raise DomainError(
            "You do not have a %s profile." % role,
            code="role_not_held",
        )

    user.active_role = role
    user.save(update_fields=["active_role", "updated_at"]
              if hasattr(user, "updated_at") else ["active_role"])
    return user


# ------------------------------------------------------------------------ otp
def _recent_send_count(phone, within=timedelta(hours=1)):
    return PhoneOTP.objects.filter(
        phone=phone, created_at__gte=timezone.now() - within
    ).count()


@transaction.atomic
def send_phone_otp(*, phone, purpose=PhoneOTP.Purpose.REGISTRATION):
    """
    Issue a 6-digit code valid for OTP_TTL_SECONDS.

    Rate limited to OTP_MAX_SENDS_PER_HOUR per number (PRD FR-1.2). Returns
    the PhoneOTP row; the plaintext code is never returned to the caller --
    in development it is logged instead (see dev.OTP_ECHO_TO_LOG).
    """
    phone = normalise_bd_phone(phone)

    if _recent_send_count(phone) >= settings.OTP_MAX_SENDS_PER_HOUR:
        raise RateLimited(
            "Too many verification codes requested. Try again in an hour.",
            details={"phone": phone},
        )

    # Supersede any outstanding code so only the newest can be used.
    PhoneOTP.objects.filter(
        phone=phone, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=timezone.now())

    code = PhoneOTP.generate_code()
    otp = PhoneOTP.objects.create(
        phone=phone,
        code_hash=PhoneOTP.hash_code(phone, code),
        purpose=purpose,
        expires_at=PhoneOTP.default_expiry(),
    )

    _deliver_otp(phone, code)
    return otp


def _deliver_otp(phone, code):
    """
    Send the code.

    Phase 1 has no SMS provider, so development logs the code and production
    will dispatch through the notifications app. Kept separate so the
    delivery mechanism can change without touching the issuing logic.
    """
    if getattr(settings, "OTP_ECHO_TO_LOG", False):
        logger.info("OTP for %s is %s", phone, code)
    else:
        logger.info("OTP issued for %s (delivery pending SMS provider)", phone)


def verify_phone_otp(*, phone, code, purpose=PhoneOTP.Purpose.REGISTRATION):
    """
    Consume a code and mark the phone verified.

    Returns the User when one exists for that number, else None (the
    registration flow verifies before the account is usable).

    NOTE ON TRANSACTIONS: this function is deliberately *not* wrapped in a
    single atomic block. A failed attempt must increment and COMMIT the
    attempt counter -- if the increment shared a transaction with the
    VerificationError that follows it, the rollback would discard the count
    and the attempt limit would never be reached, leaving the code open to
    unlimited brute-force guessing. The counter is therefore committed in its
    own transaction, and only the success path is atomic.
    """
    phone = normalise_bd_phone(phone)

    # --- read and validate, committing any attempt charge immediately -----
    with transaction.atomic():
        otp = (
            PhoneOTP.objects
            .select_for_update()
            .filter(phone=phone, purpose=purpose, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )

        if otp is None:
            raise VerificationError(
                "No verification code was requested for that number.",
                code="otp_not_found",
            )

        if otp.is_expired:
            raise VerificationError(
                "That code has expired. Request a new one.",
                code="otp_expired",
            )

        if otp.attempts >= settings.OTP_MAX_VERIFY_ATTEMPTS:
            raise RateLimited(
                "Too many incorrect attempts. Request a new code.",
                details={"phone": phone},
            )

        matched = otp.matches(code)
        if not matched:
            # Charge the attempt inside this block so it commits when the
            # block exits, before the error is raised below.
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            remaining = settings.OTP_MAX_VERIFY_ATTEMPTS - otp.attempts

    if not matched:
        raise VerificationError(
            "That code is not correct.",
            code="otp_mismatch",
            details={"attempts_remaining": max(remaining, 0)},
        )

    # --- success path: consume the code and verify the user atomically ----
    with transaction.atomic():
        otp.consumed_at = timezone.now()
        otp.save(update_fields=["consumed_at"])

        user = User.objects.select_for_update().filter(phone=phone).first()
        if user and not user.phone_verified:
            user.phone_verified = True
            user.save(update_fields=["phone_verified"])
            logger.info("Phone verified for user %s", user.id)

    return user


def purge_expired_otps(*, older_than_hours=24):
    """
    Delete spent and expired codes.

    Called by `manage.py purge_otps`; replaces Redis TTL in Phase 1
    (PRD 8.4). Idempotent -- a repeated run simply finds nothing.
    """
    cutoff = timezone.now() - timedelta(hours=older_than_hours)
    deleted, _ = PhoneOTP.objects.filter(created_at__lt=cutoff).delete()
    return deleted
