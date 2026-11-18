import base64
import hashlib
import secrets
import urllib.parse
from app.main import app
from starlette.testclient import TestClient

client = TestClient(app, follow_redirects=False)

print("=== 1. TEST RFC 8414 DISCOVERY METADATA ===")
r = client.get("/.well-known/oauth-authorization-server")
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
meta = r.json()
print("Metadata Status:", r.status_code)
print("Issuer:", meta["issuer"])
print("Auth Endpoint:", meta["authorization_endpoint"])
print("Token Endpoint:", meta["token_endpoint"])
print("Registration Endpoint:", meta["registration_endpoint"])
assert meta["code_challenge_methods_supported"] == ["S256"]
assert meta["client_id_metadata_document_supported"] is True
assert meta["authorization_response_iss_parameter_supported"] is True
print("✓ Metadata checks passed!")

print("\n=== 2. TEST RFC 7591 DYNAMIC CLIENT REGISTRATION ===")
r = client.post("/oauth/register", json={
    "client_name": "ChatGPT MilesWeb Plugin",
    "redirect_uris": ["https://chatgpt.com/aip/callback"]
})
assert r.status_code == 201, f"Expected 201, got {r.status_code}"
reg = r.json()
print("Registered Client ID:", reg["client_id"])
print("Registered Client Name:", reg["client_name"])
print("Token Auth Method:", reg["token_endpoint_auth_method"])
assert reg["token_endpoint_auth_method"] == "none"
print("✓ Client registration passed!")

print("\n=== 3. TEST GET /oauth/authorize (HTML POPUP) ===")
# Generate PKCE code_verifier and code_challenge
code_verifier = secrets.token_urlsafe(40)
code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")

r = client.get(f"/oauth/authorize?client_id={reg['client_id']}&redirect_uri=https://example.com/callback&state=teststate123&code_challenge={code_challenge}&code_challenge_method=S256")
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
assert "text/html" in r.headers["content-type"]
assert "MilesWeb Authorization" in r.text
assert "Already Have Account" in r.text
assert "New User Signup" in r.text
assert "demo@milesweb.com" in r.text
print("✓ Authorize HTML popup rendered successfully!")

print("\n=== 4. TEST POST /oauth/authorize/submit (INVALID LOGIN) ===")
r = client.post("/oauth/authorize/submit", data={
    "mode": "login",
    "client_id": reg['client_id'],
    "redirect_uri": "https://example.com/callback",
    "state": "teststate123",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
    "email": "demo@milesweb.com",
    "password": "wrongpassword"
})
assert r.status_code == 303, f"Expected 303, got {r.status_code}"
assert "error_msg" in r.headers["location"]
print("✓ Invalid login redirected with error message as expected:", r.headers["location"])

print("\n=== 5. TEST POST /oauth/authorize/submit (VALID LOGIN & CODE ISSUANCE) ===")
r = client.post("/oauth/authorize/submit", data={
    "mode": "login",
    "client_id": reg['client_id'],
    "redirect_uri": "https://example.com/callback",
    "state": "teststate123",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
    "email": "demo@milesweb.com",
    "password": "password123"
})
assert r.status_code == 303, f"Expected 303, got {r.status_code}"
redirect_target = r.headers["location"]
print("Redirected to:", redirect_target)
parsed_redirect = urllib.parse.urlparse(redirect_target)
qs = urllib.parse.parse_qs(parsed_redirect.query)
assert "code" in qs, "Code missing from redirect"
assert qs["code"][0].startswith("mw_code_"), "Code format invalid"
assert qs["iss"][0] == meta["issuer"], "iss parameter mismatch"
assert qs["state"][0] == "teststate123", "state parameter mismatch"
auth_code = qs["code"][0]
print("Issued Code:", auth_code)
print("✓ Authorize code issuance passed!")

print("\n=== 6. TEST POST /oauth/token (PKCE S256 TOKEN EXCHANGE) ===")
# Test invalid code_verifier
r_fail = client.post("/oauth/token", data={
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": "https://example.com/callback",
    "code_verifier": "wrong_verifier"
})
assert r_fail.status_code == 400
assert r_fail.json()["error"] == "invalid_grant"
print("✓ PKCE mismatch rejected with 400 invalid_grant!")

# Re-issue a code for successful exchange
r = client.post("/oauth/authorize/submit", data={
    "mode": "login",
    "client_id": reg['client_id'],
    "redirect_uri": "https://example.com/callback",
    "state": "teststate123",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
    "email": "demo@milesweb.com",
    "password": "password123"
})
auth_code = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["location"]).query)["code"][0]

# Exchange with valid code_verifier
r_token = client.post("/oauth/token", data={
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": "https://example.com/callback",
    "code_verifier": code_verifier
})
assert r_token.status_code == 200, f"Token exchange failed: {r_token.text}"
token_data = r_token.json()
print("Token Response:", token_data)
assert "access_token" in token_data
assert token_data["token_type"] == "Bearer"
assert token_data["expires_in"] == 28800
access_token = token_data["access_token"]
print("✓ Token exchange passed!")

# Single-use test: re-using the same code must fail
r_reuse = client.post("/oauth/token", data={
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": "https://example.com/callback",
    "code_verifier": code_verifier
})
assert r_reuse.status_code == 400
assert r_reuse.json()["error"] == "invalid_grant"
print("✓ Code single-use verification passed (second exchange rejected)!")

print("\n=== 7. TEST GET /api/auth/me (BEARER TOKEN VERIFICATION) ===")
r_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})
assert r_me.status_code == 200, f"Failed /api/auth/me: {r_me.text}"
user_profile = r_me.json()
print("User Profile from token:", user_profile)
assert user_profile["email"] == "demo@milesweb.com"
assert user_profile["name"] == "Demo User"
assert user_profile["org_id"] == "c1a2b3d4-e5f6-7890-abcd-ef1234567890"
print("✓ Bearer token claims verified successfully!")

print("\n=== 8. TEST SIGNUP FLOW WITH NEW USER ===")
new_verifier = secrets.token_urlsafe(40)
new_challenge = base64.urlsafe_b64encode(hashlib.sha256(new_verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")

r_signup = client.post("/oauth/authorize/submit", data={
    "mode": "signup",
    "client_id": reg['client_id'],
    "redirect_uri": "https://example.com/callback",
    "state": "signupstate456",
    "code_challenge": new_challenge,
    "code_challenge_method": "S256",
    "first_name": "Soham",
    "last_name": "Sonawane",
    "email": "soham@milesweb.com",
    "password": "securepassword123",
    "phone": "+919876543210",
    "country": "India",
    "state_name": "Maharashtra",
    "city": "Nashik",
    "postcode": "422001"
})
assert r_signup.status_code == 303
signup_code = urllib.parse.parse_qs(urllib.parse.urlparse(r_signup.headers["location"]).query)["code"][0]

r_signup_token = client.post("/oauth/token", data={
    "grant_type": "authorization_code",
    "code": signup_code,
    "redirect_uri": "https://example.com/callback",
    "code_verifier": new_verifier
})
assert r_signup_token.status_code == 200
signup_access_token = r_signup_token.json()["access_token"]

r_new_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {signup_access_token}"})
assert r_new_me.status_code == 200
new_profile = r_new_me.json()
print("Newly Signed-Up User Profile:", new_profile)
assert new_profile["email"] == "soham@milesweb.com"
assert new_profile["name"] == "Soham Sonawane"
assert new_profile["org_id"] == "c1a2b3d4-e5f6-7890-abcd-ef1234567890"
print("✓ Signup and subsequent authentication passed!")

print("\n🎉 ALL OAUTH 2.1 SPECIFICATION CHECKS PASSED WITH 100% SUCCESS!")
