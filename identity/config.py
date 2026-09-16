"""Explicit runtime configuration for the identity API."""

import os
from pathlib import Path


class IdentityConfigurationError(RuntimeError):
    pass


def database_url() -> str:
    value = os.environ.get("OUIVOCAL_DATABASE_URL")
    if not value:
        raise IdentityConfigurationError("Identity database is not configured")
    return value


def jwt_secret() -> str:
    secret_file = os.environ.get("OUIVOCAL_JWT_SECRET_FILE")
    if secret_file:
        try:
            value = Path(secret_file).read_text(encoding="utf-8").rstrip()
        except OSError as error:
            raise IdentityConfigurationError(
                "Identity JWT secret file is not available"
            ) from error
    else:
        value = os.environ.get("OUIVOCAL_JWT_SECRET")
    if not value or len(value) < 32:
        raise IdentityConfigurationError("Identity JWT secret is not configured")
    return value
