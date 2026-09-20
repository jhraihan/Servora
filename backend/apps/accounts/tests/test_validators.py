"""Phone normalisation and validation (PRD FR-1.1)."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import normalise_bd_phone, validate_bd_phone


@pytest.mark.parametrize("raw,expected", [
    ("+8801712345678", "+8801712345678"),
    ("8801712345678", "+8801712345678"),
    ("01712345678", "+8801712345678"),
    ("1712345678", "+8801712345678"),
    ("+880 17 1234 5678", "+8801712345678"),
    ("017-1234-5678", "+8801712345678"),
    ("  01712345678  ", "+8801712345678"),
])
def test_normalise_converges_on_canonical_form(raw, expected):
    """Every form a user might type must produce one canonical value --
    otherwise the uniqueness constraint on User.phone is meaningless."""
    assert normalise_bd_phone(raw) == expected


@pytest.mark.parametrize("valid", [
    "+8801312345678", "+8801712345678", "+8801912345678",
])
def test_valid_operator_prefixes_accepted(valid):
    validate_bd_phone(valid)


@pytest.mark.parametrize("invalid", [
    "+8801212345678",   # operator prefix 2 is not issued
    "+880171234567",    # too short
    "+88017123456789",  # too long
    "+9101712345678",   # wrong country
    "not a phone",
    "",
])
def test_invalid_numbers_rejected(invalid):
    with pytest.raises(ValidationError):
        validate_bd_phone(invalid)
