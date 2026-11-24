"""Shared HTTP Bearer security schemes and authentication dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.services.token_service import decode_access_token

http_bearer = HTTPBearer(
    scheme_name="BearerAuth",
    auto_error=False,
    description="Bearer token (dynamic JWT access token or verified test token).",
)


def get_current_client_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)] = None,
    settings: Settings = Depends(get_settings),
) -> int:
    """Extract and dynamically verify client ID from Bearer token."""
    if not credentials or not credentials.credentials.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing_token", "message": "Authorization header is required"},
        )

    token = credentials.credentials.strip()

    # 1. Attempt dynamic JWT token decode
    claims = decode_access_token(token, settings=settings)
    if claims:
        raw_id = claims.get("clientId") or claims.get("sub")
        if raw_id is not None and str(raw_id).isdigit():
            return int(raw_id)

    # 2. Development test tokens fallback (e.g. mock-token-rahul:12345, mock-token-amit:12346)
    for item in settings.phase2_test_tokens.split(","):
        test_token, separator, client_id = item.strip().partition(":")
        if separator and test_token == token and client_id.isdigit():
            return int(client_id)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "invalid_token", "message": "Token is invalid or expired"},
    )
