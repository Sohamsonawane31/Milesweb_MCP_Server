"""Dynamic JWT token creation, decoding, and validation service."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.config import Settings, get_settings


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    """Create a signed JWT access token with an expiration time."""
    active_settings = settings or get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=active_settings.jwt_expires_in_minutes)

    to_encode.update({
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    })
    encoded_jwt = jwt.encode(
        to_encode,
        active_settings.jwt_secret_key,
        algorithm=active_settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(
    token: str,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    """Decode and validate a signed JWT access token.

    Returns the payload dictionary if valid and unexpired; returns None
    if the token is invalid, expired, or malformed.
    """
    active_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            active_settings.jwt_secret_key,
            algorithms=[active_settings.jwt_algorithm],
        )
        return payload
    except jwt.PyJWTError:
        return None


def verify_access_token(
    token: str,
    settings: Settings | None = None,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    """Verify a token and return (is_valid, payload, error_message).

    Useful for introspection and explicit verification endpoints.
    """
    active_settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            active_settings.jwt_secret_key,
            algorithms=[active_settings.jwt_algorithm],
        )
        return True, payload, None
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
    except jwt.InvalidSignatureError:
        return False, None, "Token signature is invalid"
    except jwt.DecodeError:
        return False, None, "Token format is malformed or invalid"
    except jwt.PyJWTError as exc:
        return False, None, f"Token validation error: {str(exc)}"
