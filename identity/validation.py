"""Server-side validation for permanent OuiVocal identities."""

import re

OFFICIAL_LANGUAGES = frozenset({"en", "fr", "es", "zh", "ru", "ar"})
OUIVOCAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class ValidationError(ValueError):
    """A client supplied an invalid identity field."""


def normalize_ouivocal_id(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("OuiVocal ID is required")
    normalized = value.strip().lower()
    if not OUIVOCAL_ID_PATTERN.fullmatch(value.strip()):
        raise ValidationError(
            "OuiVocal ID must be 3–30 letters, numbers, or underscores"
        )
    return normalized


def normalize_email(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("Email is required")
    normalized = value.strip().lower()
    if len(normalized) > 254 or not EMAIL_PATTERN.fullmatch(normalized):
        raise ValidationError("A valid email address is required")
    return normalized


def require_password(value: object) -> str:
    if not isinstance(value, str) or len(value) < 12 or len(value) > 256:
        raise ValidationError("Password must be between 12 and 256 characters")
    return value


def require_language(value: object, field_name: str) -> str:
    if value not in OFFICIAL_LANGUAGES:
        raise ValidationError(f"{field_name} must be an official OuiVocal language")
    return str(value)


def optional_language(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return require_language(value, field_name)


def optional_text(value: object, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be text")
    cleaned = value.strip()
    if len(cleaned) > maximum:
        raise ValidationError(f"{field_name} must be at most {maximum} characters")
    return cleaned or None
