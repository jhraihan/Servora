"""Bangladesh-specific field validation (PRD FR-1.1)."""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# +8801XXXXXXXXX -- 11 national digits beginning 01, operator prefix 3-9.
BD_PHONE_RE = re.compile(r"^\+8801[3-9]\d{8}$")


def validate_bd_phone(value):
    if not BD_PHONE_RE.match(value or ""):
        raise ValidationError(
            _("Enter a valid Bangladeshi mobile number, e.g. +8801712345678."),
            code="invalid_phone",
        )


def normalise_bd_phone(value):
    """
    Accept the forms people actually type and return canonical +8801XXXXXXXXX.

    Normalising at the boundary means the uniqueness constraint on
    User.phone is meaningful -- otherwise 01712345678 and +8801712345678
    would be two different accounts for one person.
    """
    if not value:
        return value

    digits = re.sub(r"[\s\-()]", "", value.strip())

    if digits.startswith("+88"):
        pass
    elif digits.startswith("88"):
        digits = "+" + digits
    elif digits.startswith("0"):
        digits = "+88" + digits
    elif digits.startswith("1") and len(digits) == 10:
        digits = "+880" + digits
    else:
        digits = digits if digits.startswith("+") else "+" + digits

    return digits
