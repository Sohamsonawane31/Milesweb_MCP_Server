"""Tests for authentication, dynamic JWT tokens, and token verification."""

from datetime import timedelta
import pytest
from app.services.token_service import create_access_token


def test_login_success_rahul(client):
    """Logging in with an existing user in dummy data returns their specific clientId and a dynamic JWT token."""
    response = client.post(
        "/auth/login",
        json={"email": "rahul@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "rahul@example.com"
    assert data["clientId"] == "12345"
    assert data["name"] == "Rahul Sharma"
    assert data["tokenType"] == "bearer"
    assert data["token"] != "mock-token-rahul"  # Ensure it is dynamic, not the old static string
    assert len(data["token"]) > 20


def test_login_success_amit(client):
    """Logging in as Amit returns Amit's clientId (12346), not Rahul's hardcoded clientId."""
    response = client.post(
        "/auth/login",
        json={"email": "amit@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "amit@example.com"
    assert data["clientId"] == "12346"
    assert data["name"] == "Amit Patil"


def test_login_rejects_unknown_user(client):
    """Users that do not exist in dummy data are rejected with 401."""
    response = client.post(
        "/auth/login",
        json={"email": "notfound@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    error = response.json()["detail"]
    assert error["error"] == "user_not_found"


def test_login_rejects_wrong_password(client):
    """When a customer has a configured password, incorrect password returns 401."""
    response = client.post(
        "/auth/login",
        json={"email": "rahul@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "invalid_credentials"


@pytest.mark.parametrize("payload", [
    {"email": "", "password": "password123"},
    {"email": "rahul@example.com", "password": "  "},
    {"email": "  ", "password": "  "},
])
def test_login_rejects_empty_credentials(client, payload):
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "missing_credentials"


def test_auth_me_with_dynamic_jwt(client):
    """Calling /auth/me with dynamic JWT token returns caller's profile."""
    login_res = client.post(
        "/auth/login",
        json={"email": "neha@example.com", "password": "password123"},
    )
    token = login_res.json()["token"]

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["clientId"] == 12348
    assert profile["name"] == "Neha Kulkarni"
    assert profile["email"] == "neha@example.com"


def test_auth_me_rejects_missing_or_invalid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer invalid-garbage-token"}).status_code == 401


def test_auth_me_with_mock_token_rahul(client):
    """Authorization: Bearer mock-token-rahul returns Rahul's profile."""
    res = client.get("/auth/me", headers={"Authorization": "Bearer mock-token-rahul"})
    assert res.status_code == 200
    profile = res.json()
    assert profile["name"] == "Rahul Sharma"
    assert profile["clientId"] == 12345
    assert profile["email"] == "rahul@example.com"


def test_auth_me_with_mock_token_amit(client):
    """Authorization: Bearer mock-token-amit returns Amit's profile."""
    res = client.get("/auth/me", headers={"Authorization": "Bearer mock-token-amit"})
    assert res.status_code == 200
    profile = res.json()
    assert profile["name"] == "Amit Patil"
    assert profile["clientId"] == 12346
    assert profile["email"] == "amit@example.com"


def test_auth_me_openapi_security(client):
    """OpenAPI schema declares BearerAuth security for /auth/me without ordinary header params."""
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/auth/me"]["get"]
    assert operation["security"] == [{"BearerAuth": []}]
    parameters = operation.get("parameters", [])
    assert not any(p.get("name") == "authorization" for p in parameters)
    schemes = schema["components"]["securitySchemes"]
    assert "BearerAuth" in schemes
    assert schemes["BearerAuth"]["type"] == "http"
    assert schemes["BearerAuth"]["scheme"] == "bearer"


def test_verify_endpoint_post(client):
    """POST /auth/verify dynamically verifies token signature and claims."""
    login_res = client.post(
        "/auth/login",
        json={"email": "rahul@example.com", "password": "password123"},
    )
    token = login_res.json()["token"]

    verify_res = client.post("/auth/verify", json={"token": token})
    assert verify_res.status_code == 200
    body = verify_res.json()
    assert body["valid"] is True
    assert body["clientId"] == "12345"
    assert body["email"] == "rahul@example.com"
    assert "exp" in body["claims"]


def test_verify_endpoint_get(client):
    """GET /auth/verify accepts Authorization header."""
    login_res = client.post(
        "/auth/login",
        json={"email": "amit@example.com", "password": "password123"},
    )
    token = login_res.json()["token"]

    verify_res = client.get("/auth/verify", headers={"Authorization": f"Bearer {token}"})
    assert verify_res.status_code == 200
    assert verify_res.json()["clientId"] == "12346"


def test_verify_endpoint_rejects_expired_token(client):
    """Expired JWT tokens are rejected by the dynamic verification endpoint."""
    expired_token = create_access_token(
        data={"clientId": 12345, "email": "rahul@example.com"},
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    verify_res = client.post("/auth/verify", json={"token": expired_token})
    assert verify_res.status_code == 401
    assert "expired" in verify_res.json()["detail"]["message"].lower()


def test_dynamic_jwt_used_in_phase2_endpoints(client):
    """A dynamic JWT token issued at /auth/login works on Phase 2 endpoints."""
    # 1. Login as Amit to obtain dynamic JWT
    login_res = client.post(
        "/auth/login",
        json={"email": "amit@example.com", "password": "password123"},
    )
    amit_token = login_res.json()["token"]

    # 2. Access Phase 2 endpoint with Amit's dynamic JWT
    headers = {
        "X-Connector-Key": "test-connector-key",
        "Authorization": f"Bearer {amit_token}",
    }
    login_check = client.get("/login", headers=headers)
    assert login_check.status_code == 200
    assert login_check.json()["email"] == "amit@example.com"

    # 3. Access Amit's website
    website_res = client.get(
        "/orgs/org-amit-001/websites/site-amit-001",
        headers=headers,
    )
    assert website_res.status_code == 200
    assert website_res.json()["domain"] == "amitworkspace.example"

    # 4. Attempt to access Rahul's resources with Amit's dynamic token -> must return 404
    cross_tenant = client.get(
        "/orgs/org-rahul-001/websites/site-rahul-001",
        headers=headers,
    )
    assert cross_tenant.status_code == 404
