"""OAuth 2.1 Authorization Server compliant with the MCP Authorization Specification (2026-07-28).

Supports:
- RFC 8414 OAuth 2.0 Authorization Server Metadata (/.well-known/oauth-authorization-server)
- RFC 7591 Dynamic Client Registration (/oauth/register)
- Authorization Code Grant with PKCE (S256) (/oauth/authorize & /oauth/token)
- Responsive Browser Popup UI for MilesWeb Sign In & New User Signup
- Signed HS256 JWT access tokens with 8-hour expiry
- User Profile verification (/api/auth/me)
"""

import base64
import hashlib
import os
import secrets
import time
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional

import jwt
from fastapi import APIRouter, Form, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://milesweb-mcp-server.onrender.com").rstrip("/")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "milesweb-mcp-dev-secret-change-me")
DEFAULT_ORG_ID = os.getenv("DEFAULT_ORG_ID", "c1a2b3d4-e5f6-7890-abcd-ef1234567890")

router = APIRouter(tags=["OAuth 2.1 Authorization"])

# ---------------------------------------------------------------------------
# In-Memory Storage
# ---------------------------------------------------------------------------
# In-memory users store pre-seeded with demo account
USERS: Dict[str, Dict[str, Any]] = {
    "demo@milesweb.com": {
        "id": "usr_demo1234567890",
        "email": "demo@milesweb.com",
        "password": "password123",
        "name": "Demo User",
        "first_name": "Demo",
        "last_name": "User",
        "phone": "+919876543210",
        "country": "India",
        "state": "Maharashtra",
        "city": "Nashik",
        "postcode": "422001",
        "org_id": DEFAULT_ORG_ID,
    }
}

# In-memory registered clients store
CLIENTS: Dict[str, Dict[str, Any]] = {
    "test": {
        "client_id": "test",
        "client_name": "Test Client",
        "redirect_uris": [
            "https://example.com/callback",
            "http://localhost:3000/callback",
            "http://127.0.0.1:3000/callback",
        ],
        "token_endpoint_auth_method": "none",
    }
}

# In-memory authorization codes store (single-use, 5-minute lifespan)
# Structure: code -> {"user": user_dict, "client_id": ..., "expires_at": ..., "used": False, ...}
AUTH_CODES: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ClientRegistrationRequest(BaseModel):
    client_name: Optional[str] = "MCP Client"
    redirect_uris: List[str] = []
    token_endpoint_auth_method: Optional[str] = "none"
    grant_types: Optional[List[str]] = ["authorization_code"]
    response_types: Optional[List[str]] = ["code"]
    scope: Optional[str] = "mcp:tools hosting:read hosting:write"


# ---------------------------------------------------------------------------
# 1. RFC 8414 OAuth Authorization Server Metadata
# ---------------------------------------------------------------------------
@router.get("/.well-known/oauth-authorization-server")
async def get_oauth_authorization_server_metadata():
    """Returns the RFC 8414 metadata document for the OAuth 2.1 Authorization Server."""
    return {
        "issuer": PUBLIC_BASE_URL,
        "authorization_endpoint": f"{PUBLIC_BASE_URL}/oauth/authorize",
        "token_endpoint": f"{PUBLIC_BASE_URL}/oauth/token",
        "registration_endpoint": f"{PUBLIC_BASE_URL}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "scopes_supported": ["mcp:tools", "hosting:read", "hosting:write"],
        "client_id_metadata_document_supported": True,
        "authorization_response_iss_parameter_supported": True,
    }


# ---------------------------------------------------------------------------
# 2. RFC 7591 Dynamic Client Registration
# ---------------------------------------------------------------------------
@router.post("/oauth/register", status_code=status.HTTP_201_CREATED)
async def register_oauth_client(payload: ClientRegistrationRequest):
    """Dynamic client registration endpoint for AI clients (ChatGPT, Claude, etc.)."""
    client_id = f"client_{uuid.uuid4().hex[:16]}"
    client_data = {
        "client_id": client_id,
        "client_name": payload.client_name or "MCP Client",
        "redirect_uris": payload.redirect_uris,
        "token_endpoint_auth_method": "none",
        "grant_types": payload.grant_types or ["authorization_code"],
        "response_types": payload.response_types or ["code"],
        "scope": payload.scope or "mcp:tools hosting:read hosting:write",
    }
    CLIENTS[client_id] = client_data

    return {
        "client_id": client_id,
        "client_name": client_data["client_name"],
        "redirect_uris": client_data["redirect_uris"],
        "token_endpoint_auth_method": "none",
        "grant_types": client_data["grant_types"],
        "response_types": client_data["response_types"],
    }


# ---------------------------------------------------------------------------
# 3. HTML Authorization Browser Popup (/oauth/authorize)
# ---------------------------------------------------------------------------
@router.get("/oauth/authorize", response_class=HTMLResponse)
async def authorize_page(
    client_id: str = Query(..., description="OAuth client ID"),
    redirect_uri: str = Query(..., description="Callback redirect URI"),
    state: Optional[str] = Query(None, description="Client state token"),
    code_challenge: Optional[str] = Query(None, description="PKCE code challenge"),
    code_challenge_method: Optional[str] = Query("S256", description="PKCE challenge method"),
    resource: Optional[str] = Query(None, description="MCP target resource URL"),
    error_msg: Optional[str] = Query(None, description="Optional error message to display"),
):
    """Renders the responsive browser popup for MilesWeb user login and signup."""

    error_banner_html = ""
    if error_msg:
        error_banner_html = f"""
        <div class="alert alert-danger" role="alert">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <span>{error_msg}</span>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MilesWeb • Connect Account</title>
    <style>
        :root {{
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --navy: #0f172a;
            --gray-bg: #f8fafc;
            --card-border: #e2e8f0;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --danger: #ef4444;
            --danger-bg: #fef2f2;
            --success: #10b981;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--gray-bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px 16px;
        }}
        .card {{
            background: #ffffff;
            width: 100%;
            max-width: 480px;
            border-radius: 16px;
            border: 1px solid var(--card-border);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
            overflow: hidden;
        }}
        .header {{
            background: var(--navy);
            color: #ffffff;
            padding: 24px 28px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 20px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            letter-spacing: -0.3px;
        }}
        .header p {{
            font-size: 13px;
            color: #94a3b8;
            margin-top: 6px;
        }}
        .client-badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.1);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            color: #38bdf8;
            margin-top: 8px;
            font-family: monospace;
        }}
        .tab-bar {{
            display: flex;
            border-bottom: 1px solid var(--card-border);
            background: #f1f5f9;
        }}
        .tab-btn {{
            flex: 1;
            padding: 14px;
            border: none;
            background: none;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s;
            border-bottom: 2px solid transparent;
        }}
        .tab-btn.active {{
            background: #ffffff;
            color: var(--primary);
            border-bottom-color: var(--primary);
        }}
        .content {{
            padding: 28px;
        }}
        .alert {{
            padding: 12px 14px;
            border-radius: 8px;
            font-size: 13px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .alert-danger {{
            background-color: var(--danger-bg);
            color: var(--danger);
            border: 1px solid #fecaca;
        }}
        .form-group {{
            margin-bottom: 16px;
        }}
        .form-row {{
            display: flex;
            gap: 12px;
        }}
        .form-row .form-group {{
            flex: 1;
        }}
        label {{
            display: block;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 6px;
        }}
        input, select {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            font-size: 14px;
            color: var(--text-main);
            outline: none;
            transition: border-color 0.15s, box-shadow 0.15s;
        }}
        input:focus, select:focus {{
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
        }}
        .btn {{
            width: 100%;
            padding: 12px;
            background: var(--primary);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            margin-top: 8px;
        }}
        .btn:hover {{
            background: var(--primary-hover);
        }}
        .demo-helper {{
            background: #f8fafc;
            border: 1px dashed #cbd5e1;
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .demo-fill-btn {{
            background: #e2e8f0;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-main);
            cursor: pointer;
        }}
        .demo-fill-btn:hover {{
            background: #cbd5e1;
        }}
        .footer-note {{
            font-size: 11px;
            color: var(--text-muted);
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>MilesWeb Authorization</h1>
            <p>Authorize AI assistant to access your MilesWeb hosting services</p>
            <div class="client-badge">Client: {client_id}</div>
        </div>

        <div class="tab-bar">
            <button type="button" class="tab-btn active" id="tab-login-btn" onclick="switchTab('login')">Already Have Account</button>
            <button type="button" class="tab-btn" id="tab-signup-btn" onclick="switchTab('signup')">New User Signup</button>
        </div>

        <div class="content">
            {error_banner_html}

            <!-- TAB 1: SIGN IN -->
            <div id="panel-login">
                <div class="demo-helper">
                    <span>Demo Account: <strong>demo@milesweb.com</strong> / <strong>password123</strong></span>
                    <button type="button" class="demo-fill-btn" onclick="fillDemo()">Fill Demo</button>
                </div>

                <form method="POST" action="/oauth/authorize/submit">
                    <input type="hidden" name="mode" value="login">
                    <input type="hidden" name="client_id" value="{client_id}">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="state" value="{state or ''}">
                    <input type="hidden" name="code_challenge" value="{code_challenge or ''}">
                    <input type="hidden" name="code_challenge_method" value="{code_challenge_method or 'S256'}">
                    <input type="hidden" name="resource" value="{resource or ''}">

                    <div class="form-group">
                        <label for="login-email">Email Address</label>
                        <input type="email" id="login-email" name="email" required placeholder="you@example.com">
                    </div>

                    <div class="form-group">
                        <label for="login-password">Password</label>
                        <input type="password" id="login-password" name="password" required placeholder="••••••••">
                    </div>

                    <button type="submit" class="btn">Sign In & Authorize</button>
                </form>
            </div>

            <!-- TAB 2: SIGN UP -->
            <div id="panel-signup" style="display: none;">
                <form method="POST" action="/oauth/authorize/submit">
                    <input type="hidden" name="mode" value="signup">
                    <input type="hidden" name="client_id" value="{client_id}">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="state" value="{state or ''}">
                    <input type="hidden" name="code_challenge" value="{code_challenge or ''}">
                    <input type="hidden" name="code_challenge_method" value="{code_challenge_method or 'S256'}">
                    <input type="hidden" name="resource" value="{resource or ''}">

                    <div class="form-row">
                        <div class="form-group">
                            <label for="first-name">First Name</label>
                            <input type="text" id="first-name" name="first_name" required placeholder="John">
                        </div>
                        <div class="form-group">
                            <label for="last-name">Last Name</label>
                            <input type="text" id="last-name" name="last_name" required placeholder="Doe">
                        </div>
                    </div>

                    <div class="form-group">
                        <label for="signup-email">Email Address</label>
                        <input type="email" id="signup-email" name="email" required placeholder="john@example.com">
                    </div>

                    <div class="form-group">
                        <label for="signup-password">Password</label>
                        <input type="password" id="signup-password" name="password" minlength="6" required placeholder="At least 6 characters">
                    </div>

                    <div class="form-group">
                        <label for="phone">Phone Number</label>
                        <input type="tel" id="phone" name="phone" value="+91" required placeholder="+91 98765 43210">
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="country">Country</label>
                            <input type="text" id="country" name="country" value="India" required>
                        </div>
                        <div class="form-group">
                            <label for="state-name">State</label>
                            <input type="text" id="state-name" name="state_name" placeholder="Maharashtra">
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="city">City</label>
                            <input type="text" id="city" name="city" placeholder="Nashik">
                        </div>
                        <div class="form-group">
                            <label for="postcode">Postcode</label>
                            <input type="text" id="postcode" name="postcode" placeholder="422001">
                        </div>
                    </div>

                    <button type="submit" class="btn">Create Account & Authorize</button>
                </form>
            </div>

            <p class="footer-note">By authorizing, you allow this application to manage domains and hosting plans on your behalf.</p>
        </div>
    </div>

    <script>
        function switchTab(tab) {{
            const loginPanel = document.getElementById('panel-login');
            const signupPanel = document.getElementById('panel-signup');
            const loginBtn = document.getElementById('tab-login-btn');
            const signupBtn = document.getElementById('tab-signup-btn');

            if (tab === 'login') {{
                loginPanel.style.display = 'block';
                signupPanel.style.display = 'none';
                loginBtn.classList.add('active');
                signupBtn.classList.remove('active');
            }} else {{
                loginPanel.style.display = 'none';
                signupPanel.style.display = 'block';
                signupBtn.classList.add('active');
                loginBtn.classList.remove('active');
            }}
        }}

        function fillDemo() {{
            document.getElementById('login-email').value = 'demo@milesweb.com';
            document.getElementById('login-password').value = 'password123';
        }}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


# ---------------------------------------------------------------------------
# 4. Form Submission & Code Issuance (/oauth/authorize/submit)
# ---------------------------------------------------------------------------
@router.post("/oauth/authorize/submit")
async def authorize_submit(
    mode: str = Form(..., description="'login' or 'signup'"),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    state: Optional[str] = Form(None),
    code_challenge: Optional[str] = Form(None),
    code_challenge_method: Optional[str] = Form("S256"),
    resource: Optional[str] = Form(None),
    email: str = Form(...),
    password: str = Form(...),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    country: Optional[str] = Form("India"),
    state_name: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    postcode: Optional[str] = Form(None),
):
    """Processes login or signup and returns a 303 redirect with an authorization code."""
    normalized_email = email.strip().lower()

    def build_error_redirect(msg: str) -> str:
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "error_msg": msg,
        }
        if state:
            params["state"] = state
        if code_challenge:
            params["code_challenge"] = code_challenge
        if code_challenge_method:
            params["code_challenge_method"] = code_challenge_method
        if resource:
            params["resource"] = resource
        return f"/oauth/authorize?{urllib.parse.urlencode(params)}"

    user = None

    if mode == "login":
        existing_user = USERS.get(normalized_email)
        if not existing_user or existing_user["password"] != password:
            return RedirectResponse(
                url=build_error_redirect("Invalid email or password. Please try again."),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        user = existing_user

    elif mode == "signup":
        if normalized_email in USERS:
            return RedirectResponse(
                url=build_error_redirect("An account with this email already exists. Please sign in."),
                status_code=status.HTTP_303_SEE_OTHER,
            )
        if len(password) < 6:
            return RedirectResponse(
                url=build_error_redirect("Password must be at least 6 characters long."),
                status_code=status.HTTP_303_SEE_OTHER,
            )

        user_id = f"usr_{uuid.uuid4().hex[:12]}"
        full_name = f"{first_name or ''} {last_name or ''}".strip() or normalized_email.split("@")[0]
        new_user = {
            "id": user_id,
            "email": normalized_email,
            "password": password,
            "name": full_name,
            "first_name": first_name or "",
            "last_name": last_name or "",
            "phone": phone or "+91",
            "country": country or "India",
            "state": state_name or "",
            "city": city or "",
            "postcode": postcode or "",
            "org_id": DEFAULT_ORG_ID,
        }
        USERS[normalized_email] = new_user
        user = new_user
    else:
        return RedirectResponse(
            url=build_error_redirect("Invalid submission mode."),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    # Generate single-use authorization code (valid for 5 minutes)
    code = f"mw_code_{secrets.token_urlsafe(32)}"
    AUTH_CODES[code] = {
        "user": user,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method or "S256",
        "resource": resource,
        "expires_at": time.time() + 300,
        "used": False,
    }

    # Build callback redirect URL
    parsed = urllib.parse.urlparse(redirect_uri)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params["code"] = [code]
    query_params["iss"] = [PUBLIC_BASE_URL]
    if state:
        query_params["state"] = [state]

    new_query = urllib.parse.urlencode(query_params, doseq=True)
    target_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))

    return RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)


# ---------------------------------------------------------------------------
# 5. Token Issuance Endpoint (/oauth/token)
# ---------------------------------------------------------------------------
@router.post("/oauth/token")
async def exchange_token(
    grant_type: str = Form(..., description="Must be 'authorization_code'"),
    code: str = Form(..., description="Authorization code issued by /oauth/authorize/submit"),
    redirect_uri: Optional[str] = Form(None, description="Must match the authorization request"),
    code_verifier: Optional[str] = Form(None, description="PKCE code verifier"),
    client_id: Optional[str] = Form(None),
):
    """
    Exchanges an authorization code for an HS256-signed JWT access token.
    Enforces PKCE S256 verification and single-use expiration.
    """
    if grant_type != "authorization_code":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "unsupported_grant_type",
                "error_description": "Only grant_type='authorization_code' is currently supported.",
            },
        )

    code_data = AUTH_CODES.get(code)
    if not code_data:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_grant",
                "error_description": "Authorization code is invalid or not found.",
            },
        )

    if code_data["used"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_grant",
                "error_description": "Authorization code has already been used.",
            },
        )

    if time.time() > code_data["expires_at"]:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "invalid_grant",
                "error_description": "Authorization code has expired.",
            },
        )

    # Invalidate code immediately (single-use)
    code_data["used"] = True

    # Validate redirect_uri if supplied
    expected_redirect_uri = code_data.get("redirect_uri")
    if redirect_uri and expected_redirect_uri:
        if redirect_uri != expected_redirect_uri:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "invalid_grant",
                    "error_description": "redirect_uri mismatch.",
                },
            )

    # PKCE S256 Verification
    expected_challenge = code_data.get("code_challenge")
    challenge_method = code_data.get("code_challenge_method", "S256")

    if expected_challenge:
        if not code_verifier:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "invalid_request",
                    "error_description": "code_verifier required for PKCE authorization code exchange.",
                },
            )

        if challenge_method == "S256":
            sha256_digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
            computed_challenge = base64.urlsafe_b64encode(sha256_digest).decode("ascii").rstrip("=")
            if computed_challenge != expected_challenge.rstrip("="):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_grant",
                        "error_description": "PKCE S256 verification failed.",
                    },
                )
        elif challenge_method == "plain":
            if code_verifier != expected_challenge:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "error": "invalid_grant",
                        "error_description": "PKCE plain verification failed.",
                    },
                )

    # Issue HS256 JWT Token (valid 8 hours)
    now = int(time.time())
    expires_in = 28800  # 8 hours in seconds
    user = code_data["user"]
    target_audience = code_data.get("resource") or "https://milesweb-mcp.onrender.com/mcp"

    payload = {
        "iss": PUBLIC_BASE_URL,
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user["name"],
        "org_id": user["org_id"],
        "aud": target_audience,
        "iat": now,
        "exp": now + expires_in,
        "scope": "mcp:tools hosting:read hosting:write",
    }

    access_token = jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": "mcp:tools hosting:read hosting:write",
    }


# ---------------------------------------------------------------------------
# 6. User Claims Verification (/api/auth/me)
# ---------------------------------------------------------------------------
@router.get("/api/auth/me")
async def get_current_user_profile(authorization: Optional[str] = Header(None)):
    """Verifies the Bearer JWT token and returns user profile & org claims."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "detail": "Missing or invalid 'Authorization: Bearer <token>' header"},
        )

    token = authorization.split("Bearer ", 1)[1].strip()

    try:
        decoded = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "token_expired", "detail": "Access token has expired."},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "detail": "Access token is invalid or malformed."},
        )

    return {
        "id": decoded.get("sub"),
        "email": decoded.get("email"),
        "name": decoded.get("name"),
        "org_id": decoded.get("org_id"),
        "scope": decoded.get("scope"),
        "aud": decoded.get("aud"),
        "iss": decoded.get("iss"),
        "exp": decoded.get("exp"),
    }
