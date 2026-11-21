from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(request: Request):
    """
    Dummy mock login endpoint for client-side login integration testing only.

    Accepts any non-empty email/password combination without enforcing real
    password hashing or database lookup. This endpoint must be replaced with
    proper authentication before production deployment.

    Returns a dummy access token suitable for development/testing purposes.

    Validation: Returns HTTP 400 with a clear JSON error message if either
    email or password is missing or empty. Does not enforce real password
    hashing or database lookup - accepts any non-empty credentials for testing.
    """
    # Read raw body for manual validation (to return 400 instead of default 422)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_json",
                "message": "Request body must be valid JSON",
            },
        )

    email = body.get("email")
    password = body.get("password")

    # Validate that both fields are present and non-empty
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "missing_credentials",
                "message": "Both email and password are required",
            },
        )

    # Dummy authentication - accept any non-empty credentials for testing
    return {
        "email": email,
        "clientId": "test-client-001",
        "token": "dummy_test_token_1234567890",
    }