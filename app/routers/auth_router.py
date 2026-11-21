from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(
        ...,
        examples=["demo@milesweb.com"],
        description="User email address",
    )
    password: str = Field(
        ...,
        examples=["password123"],
        description="User account password",
    )


class LoginResponse(BaseModel):
    email: str
    clientId: str
    token: str


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """
    Dummy mock login endpoint for client-side login integration testing.

    Accepts any non-empty email/password combination for development/testing.
    Returns a dummy access token suitable for integration testing.
    """
    if not payload.email.strip() or not payload.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_credentials",
                "message": "Both email and password are required and cannot be empty",
            },
        )

    return LoginResponse(
        email=payload.email.strip(),
        clientId="test-client-001",
        token="dummy_test_token_1234567890",
    )
