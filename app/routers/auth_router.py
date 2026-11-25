"""Authentication and token verification routes."""

import hashlib
import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.customer_repository import CustomerRepository, repository
from app.security import get_current_client_id, http_bearer
from app.services.token_service import (
    create_access_token,
    decode_access_token,
    verify_access_token,
)


def _verify_password(plain_password: str, stored: str) -> bool:
    """Verify a password against a pbkdf2_sha256:{salt}:{hash} entry.

    Uses constant-time comparison to prevent timing attacks.
    Falls back to accepting any password when no hash is stored
    (backward-compat only — all fixture entries must have a hash).
    """
    if not stored or not stored.startswith("pbkdf2_sha256:"):
        # No hash configured — this customer entry is incomplete; deny access.
        return False
    try:
        _, salt, expected_hex = stored.split(":", 2)
    except ValueError:
        return False
    candidate_hex = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode(), salt.encode(), 260000
    ).hex()
    return hmac.compare_digest(candidate_hex, expected_hex)

router = APIRouter(prefix="/auth", tags=["auth"])


def get_repository() -> CustomerRepository:
    return repository


class LoginRequest(BaseModel):
    email: str = Field(
        ...,
        examples=["rahul@example.com"],
        description="User email address (e.g. rahul@example.com, amit@example.com, neha@example.com)",
    )
    password: str = Field(
        ...,
        examples=["password123"],
        description="User account password (default: password123)",
    )


class LoginResponse(BaseModel):
    email: str
    clientId: str
    token: str
    name: str | None = None
    tokenType: str = "bearer"


class VerifyTokenRequest(BaseModel):
    token: str = Field(
        ...,
        description="JWT access token to verify dynamically",
    )


class VerifyTokenResponse(BaseModel):
    valid: bool
    clientId: str
    email: str
    name: str | None = None
    claims: dict[str, Any]


class UserProfileResponse(BaseModel):
    clientId: int
    name: str
    email: str
    status: str


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    customer_repo: CustomerRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    """
    Authenticate user against dummy customer fixture data.

    Checks whether the email exists in dummy data (`data/customers.json`).
    If found and credentials match, generates and returns a dynamic signed
    JWT access token with customer details and clientId.
    """
    email_clean = payload.email.strip()
    password_clean = payload.password.strip()

    if not email_clean or not password_clean:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_credentials",
                "message": "Both email and password are required and cannot be empty",
            },
        )

    customer = customer_repo.get_customer_by_email(email_clean)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "user_not_found",
                "message": f"User with email '{email_clean}' does not exist in dummy data",
            },
        )

    # Validate password against the stored PBKDF2 hash
    stored_hash = customer.get("password_hash")
    if not _verify_password(payload.password, stored_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_credentials",
                "message": "Invalid password",
            },
        )

    # Generate a dynamic signed JWT access token for this customer
    token = create_access_token(
        data={
            "sub": str(customer["clientId"]),
            "clientId": customer["clientId"],
            "email": customer["email"],
            "name": customer.get("name", ""),
        },
        settings=settings,
    )

    return LoginResponse(
        email=customer["email"],
        clientId=str(customer["clientId"]),
        token=token,
        name=customer.get("name"),
        tokenType="bearer",
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    client_id: int = Depends(get_current_client_id),
    customer_repo: CustomerRepository = Depends(get_repository),
):
    """
    Dynamically identify and return the profile of the authenticated caller
    from their Bearer JWT token.
    """
    customer = customer_repo.get_customer(client_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Customer record not found"},
        )
    return UserProfileResponse(
        clientId=customer["clientId"],
        name=customer["name"],
        email=customer["email"],
        status=customer["status"],
    )


def parse_token_input(token_str: str) -> str:
    cleaned = token_str.strip().strip('"').strip("'")
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned


@router.post("/verify", response_model=VerifyTokenResponse)
async def verify_token_post(
    payload: VerifyTokenRequest,
    customer_repo: CustomerRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    """
    Dynamically verify an access token supplied in the request body.

    Validates signature, expiration, and extracts claims without hardcoded values.
    Also supports development test tokens.
    """
    token_clean = parse_token_input(payload.token)
    is_valid, claims, error_message = verify_access_token(token_clean, settings=settings)
    if is_valid and claims:
        raw_id = claims.get("clientId") or claims.get("sub", "")
        return VerifyTokenResponse(
            valid=True,
            clientId=str(raw_id),
            email=claims.get("email", ""),
            name=claims.get("name"),
            claims=claims,
        )

    # Development test tokens fallback (e.g. mock-token-rahul, mock-token-amit)
    for item in settings.phase2_test_tokens.split(","):
        test_token, separator, client_id = item.strip().partition(":")
        if separator and test_token == token_clean and client_id.isdigit():
            customer = customer_repo.get_customer(int(client_id))
            return VerifyTokenResponse(
                valid=True,
                clientId=client_id,
                email=customer.get("email", "") if customer else "",
                name=customer.get("name") if customer else None,
                claims={"sub": client_id, "clientId": int(client_id), "token_type": "test_token"},
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "invalid_token", "message": error_message or "Token is invalid"},
    )


@router.get("/verify", response_model=VerifyTokenResponse)
async def verify_token_get(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)] = None,
    token: Annotated[str | None, Query(description="Token to verify if not passed in header")] = None,
    customer_repo: CustomerRepository = Depends(get_repository),
    settings: Settings = Depends(get_settings),
):
    """
    Dynamically verify an access token passed in Authorization header or query parameter.
    """
    bearer_token = token
    if credentials and credentials.credentials.strip():
        bearer_token = credentials.credentials.strip()

    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "missing_token", "message": "Token must be provided in Authorization header or token query parameter"},
        )

    token_clean = parse_token_input(bearer_token)
    is_valid, claims, error_message = verify_access_token(token_clean, settings=settings)
    if is_valid and claims:
        raw_id = claims.get("clientId") or claims.get("sub", "")
        return VerifyTokenResponse(
            valid=True,
            clientId=str(raw_id),
            email=claims.get("email", ""),
            name=claims.get("name"),
            claims=claims,
        )

    # Development test tokens fallback (e.g. mock-token-rahul, mock-token-amit)
    for item in settings.phase2_test_tokens.split(","):
        test_token, separator, client_id = item.strip().partition(":")
        if separator and test_token == token_clean and client_id.isdigit():
            customer = customer_repo.get_customer(int(client_id))
            return VerifyTokenResponse(
                valid=True,
                clientId=client_id,
                email=customer.get("email", "") if customer else "",
                name=customer.get("name") if customer else None,
                claims={"sub": client_id, "clientId": int(client_id), "token_type": "test_token"},
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "invalid_token", "message": error_message or "Token is invalid"},
    )
