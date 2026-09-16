"""Password and token primitives for the identity API."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from identity.config import jwt_secret

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # Werkzeug's scrypt is deliberately selected rather than its legacy PBKDF2 default.
    return generate_password_hash(password, method="scrypt")


def password_matches(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def token_digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def issue_access_token(user_id: str) -> str:
    import jwt
    now = datetime.now(UTC)
    return jwt.encode(
        {"sub": user_id, "type": "access", "iat": now, "exp": now + ACCESS_TOKEN_TTL},
        jwt_secret(),
        algorithm=ALGORITHM,
    )


def issue_refresh_token(user_id: str, family_id: str | None = None) -> tuple[str, str, datetime, str, str]:
    raw_token = str(uuid4()) + str(uuid4())
    expires_at = datetime.now(UTC) + REFRESH_TOKEN_TTL
    return raw_token, token_digest(raw_token), expires_at, str(uuid4()), family_id or str(uuid4())


def decode_access_token(token: str) -> str:
    import jwt
    payload = jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM])
    if payload.get("type") != "access" or not isinstance(payload.get("sub"), str):
        raise jwt.InvalidTokenError("Invalid access token")
    return payload["sub"]
