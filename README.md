# MilesWeb Enhance Mock API

A **read-only FastAPI mock backend** that simulates the MilesWeb customer API and Enhance hosting panel API. It is the development and testing backend for the **MilesWeb MCP server** (`milesweb_mcp`), which connects Claude / ChatGPT to MilesWeb hosting accounts.

---

## Architecture

```
Claude / ChatGPT
      │
      ▼  MCP protocol
MCP Server  (milesweb_mcp — deployed on Render)
      │
      ▼  HTTP  (X-Connector-Key + Bearer token)
This mock backend  (enhance-mock-api — port 8000)
      │
      ▼  reads
data/customers.json  (fixture data — never written)
```

The MCP server never trusts a raw `clientId` argument from the AI. It derives the customer identity from the verified Bearer JWT and passes it to this service using the shared `CONNECTOR_API_KEY`.

---

## Project layout

```
app/
  config.py                  environment + settings (pydantic-settings)
  customer_repository.py     read-only fixture data access layer
  main.py                    FastAPI application entry point
  openapi.py                 OpenAPI / Swagger UI customization
  security.py                shared HTTPBearer authentication dependency
  routers/
    auth_router.py           /auth login and token verification endpoints
    customer_router.py       /api/v1/connector/customer endpoints
    phase2_router.py         35 Phase 2 Enhance mock GET operations
  services/
    phase2_catalog.py        Enhance mock data provider + tenant isolation
    token_service.py         JWT creation and verification (HS256, PBKDF2)
data/
  customers.json             single consolidated fixture (users + hosting + Enhance data)
tests/
  conftest.py                shared fixtures and test client setup
  test_auth.py               authentication, JWT, login tests
  test_customer_connector.py connector API and tenant isolation tests
  test_phase2_catalog.py     Phase 2 operations and authorization tests
  test_audit_gaps.py         edge-case and regression tests
requirements.txt
.env.example
```

---

## Quick start

Python 3.11+ recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env — set CONNECTOR_API_KEY to a long random secret
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Browse the full interactive API docs at **http://127.0.0.1:8000/docs**.

### Environment variables (`.env`)

| Variable | Purpose |
| --- | --- |
| `CONNECTOR_API_KEY` | Shared secret authenticating the MCP server to this backend |
| `JWT_SECRET_KEY` | HS256 signing key for dynamic access tokens |
| `PHASE2_TEST_TOKENS` | Comma-separated `token:clientId` pairs for local mock testing without login |

> [!IMPORTANT]
> `CONNECTOR_API_KEY` grants access to all customer data. Keep it out of logs, version control, and client-side code. Reference `.env.example` for the required format.

---

## Authentication rules

| Route group | Required headers |
| --- | --- |
| `GET /health` | None |
| `POST /auth/login` | `Content-Type: application/json` |
| `GET /auth/me`, `/auth/verify` | `Authorization: Bearer <token>` |
| `/api/v1/connector/*` | `X-Connector-Key: <CONNECTOR_API_KEY>` |
| `/orgs/…`, `/login`, `/v2/…`, `/websites/…` (Phase 2) | **Both:** `X-Connector-Key` + `Authorization: Bearer <token>` |

---

## Implemented APIs

### 1. System

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/health` | None | Service health check |

---

### 2. Authentication & Token Verification

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/auth/login` | None | Validate credentials → return signed JWT |
| GET | `/auth/me` | Bearer | Decode token → return customer profile |
| POST | `/auth/verify` | None | Verify token from request body `{"token": "…"}` |
| GET | `/auth/verify` | Bearer or `?token=` | Verify token from header or query param |

#### Demo accounts

All five fixture customers share password `password123`. Passwords are stored as **PBKDF2-SHA256** hashes (stdlib `hashlib`, 260 000 iterations) — no plaintext stored.

| Email | Client ID | Scenario |
| --- | --- | --- |
| `rahul@example.com` | `12345` | Active org, 1 website, 1 subscription, 1 domain |
| `amit@example.com` | `12346` | Active org, 1 website, 3 domains (1 Pending, 1 Expired) |
| `priya@example.com` | `12347` | No hosting, no domains |
| `neha@example.com` | `12348` | Suspended website, 4 domains, 2 hosting services |
| `karan@example.com` | `12349` | No hosting, 2 domains only |

```powershell
# 1. Login and capture the token
$resp = curl.exe -s -X POST "http://127.0.0.1:8000/auth/login" `
  -H "Content-Type: application/json" `
  -d '{"email": "rahul@example.com", "password": "password123"}' | ConvertFrom-Json
$token = $resp.token

# 2. Use the token
curl.exe -H "Authorization: Bearer $token" "http://127.0.0.1:8000/auth/me"
```

---

### 3. Customer Connector API

The MCP server calls these endpoints with the shared `CONNECTOR_API_KEY`. All endpoints are `GET`-only; `POST`/`PUT`/`DELETE` return `405`.

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/connector/customer?clientId=<id>` | Customer profile (name, email, status) |
| GET | `/api/v1/connector/customer/hosting-services?clientId=<id>` | Active hosting services |
| GET | `/api/v1/connector/customer/domains?clientId=<id>` | Registered domains |

**Errors:** unknown `clientId` → `404`; missing/invalid connector key → `401`; non-numeric or missing `clientId` → `422`; customer with no hosting/domains → `200` with `{"success": true, "data": []}`.

```powershell
curl.exe -H "X-Connector-Key: your-secret" `
  "http://127.0.0.1:8000/api/v1/connector/customer?clientId=12345"
```

---

### 4. Phase 2 — Enhance Mock Operations (35 endpoints)

All 35 Enhance read-only GET operations from the supplied API catalog are implemented. Each request must include **both** `X-Connector-Key` and `Authorization: Bearer <token>`. Every `org_id`, `website_id`, `subscription_id`, `domain_id`, `backup_id`, and `app_id` in the path is validated against the authenticated customer — another customer's resource returns `404`.

Websites may have multiple domain mapping IDs (primary + additional); **all** are checked during `domain_id` authorization.

| Operation name | Path |
| --- | --- |
| `getLogin` | `GET /login` |
| `getLoginMemberships` | `GET /login/memberships` |
| `getOrg` | `GET /orgs/{org_id}` |
| `getOrgActivities` | `GET /v2/orgs/{org_id}/activities` |
| `getSubscriptionsToParent` | `GET /orgs/{org_id}/subscriptions` |
| `getSubscription` | `GET /orgs/{org_id}/subscriptions/{subscription_id}` |
| `getSubscriptionBandwidthUsage` | `GET /orgs/{org_id}/subscriptions/{subscription_id}/bandwidth` |
| `getWebsites` | `GET /orgs/{org_id}/websites` |
| `getWebsite` | `GET /orgs/{org_id}/websites/{website_id}` |
| `getWebsiteApps` | `GET /orgs/{org_id}/websites/{website_id}/apps` |
| `getWebsiteMetrics` | `GET /orgs/{org_id}/websites/{website_id}/metrics` |
| `getWebsiteCgroupLimits` | `GET /orgs/{org_id}/websites/{website_id}/cgroup_limits` |
| `getWebsiteFsQuotaLimits` | `GET /orgs/{org_id}/websites/{website_id}/fs_quota_limits` |
| `getWebsiteDomainMappings` | `GET /orgs/{org_id}/websites/{website_id}/domains` |
| `getWebsiteDomainDnsZone` | `GET /orgs/{org_id}/websites/{website_id}/domains/{domain_id}/dns-zone` |
| `getWebsiteDomainMappingDnsStatus` | `GET /orgs/{org_id}/websites/{website_id}/domains/{domain_id}/dns-status` |
| `getWebsiteDomainSslCert` | `GET /v2/domains/{domain_id}/ssl` |
| `getWebsiteBackups` | `GET /orgs/{org_id}/websites/{website_id}/backups` |
| `getWebsiteBackup` | `GET /orgs/{org_id}/websites/{website_id}/backups/{backup_id}` |
| `getWebsiteEmails` | `GET /orgs/{org_id}/websites/{website_id}/emails` |
| `getFtpUsers` | `GET /orgs/{org_id}/websites/{website_id}/ftp/users` |
| `getWebsiteMySQLDBs` | `GET /orgs/{org_id}/websites/{website_id}/mysql-dbs` |
| `getWebsiteMySQLUsers` | `GET /orgs/{org_id}/websites/{website_id}/mysql-users` |
| `getWebsitePostgresqlDbs` | `GET /orgs/{org_id}/websites/{website_id}/postgresql-dbs` |
| `getWebsitePostgresqlUsers` | `GET /orgs/{org_id}/websites/{website_id}/postgresql-users` |
| `getWebsiteSshKeys` | `GET /orgs/{org_id}/websites/{website_id}/ssh/keys` |
| `getWebsiteGitInfo` | `GET /orgs/{org_id}/websites/{website_id}/git` |
| `getWebsiteGitDeploys` | `GET /orgs/{org_id}/websites/{website_id}/git/deploys` |
| `getWebsiteEnabledPhpExtensions` | `GET /websites/{website_id}/php_extensions` |
| `getWebsiteLsphpSettings` | `GET /websites/{website_id}/lsphp_settings` |
| `getWebsitePhpErrorLog` | `GET /websites/{website_id}/php_error_log` |
| `getWordpressInfo` | `GET /orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/info` |
| `getWordpressPlugins` | `GET /orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/plugins` |
| `getWordpressThemes` | `GET /orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/themes` |
| `getWordpressAppVersion` | `GET /orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/version` |

```powershell
# Using a dynamic JWT token
curl.exe `
  -H "X-Connector-Key: your-secret" `
  -H "Authorization: Bearer $token" `
  "http://127.0.0.1:8000/orgs/org-rahul-001/websites/site-rahul-001"

# Or using a static test token (local dev only)
curl.exe `
  -H "X-Connector-Key: your-secret" `
  -H "Authorization: Bearer mock-token-rahul" `
  "http://127.0.0.1:8000/orgs/org-rahul-001/websites/site-rahul-001"
```

> [!NOTE]
> The `granularity` query parameter on `getWebsiteMetrics` is passed through to the fixture response so the MCP server can request `daily` or `hourly` data.

---

## Security highlights

| Concern | Implementation |
| --- | --- |
| Password storage | PBKDF2-SHA256, 260 000 iterations, per-user salt (stdlib `hashlib`) |
| Connector key comparison | `hmac.compare_digest` — constant-time, no timing oracle |
| Bearer token | HS256-signed JWT, verified on every Phase 2 and `/auth/me` request |
| Tenant isolation | Every path parameter validated against the authenticated `clientId` |
| Multi-domain ownership | Primary **and** additional domain IDs are all checked per website |
| Connector response filtering | Only whitelisted fields returned — no raw dict leaks |
| Write method blocking | All Phase 2 and connector routes are `GET`-only; other methods → `405` |
| CORS | `allow_origins=["*"]` — intentional for local dev; **lock this down before any production use** |

---

## Running tests

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

**89 tests** covering:
- Login with valid / invalid credentials
- Dynamic JWT creation, verification, and expiry
- `/auth/me` and both `/auth/verify` variants
- Connector key authentication on all three connector endpoints
- Field filtering on connector responses
- All five customer scenarios (active, suspended, no hosting, domains-only)
- Phase 2 authorization: own resources accepted, another customer's resources rejected
- Cross-customer `org_id`, `website_id`, `subscription_id`, `domain_id`, `backup_id` rejection
- Multi-domain ownership (primary + additional)
- `getOrgActivities` endpoint
- `getWebsiteMetrics` with `granularity` query param
- `Phase2Catalog.customer()` fallback path
- Edge cases: missing headers, wrong key, malformed tokens

---

## Current status — what is done

| Area | Status |
| --- | --- |
| Auth routes (login, me, verify ×2) | ✅ Complete |
| `GET /health` | ✅ Complete |
| Customer connector API (3 endpoints) | ✅ Complete |
| All 35 Phase 2 Enhance mock operations | ✅ Complete |
| Tenant isolation for all 5 path parameter types | ✅ Complete |
| Multi-domain ownership enforcement | ✅ Complete |
| PBKDF2 password hashing | ✅ Complete |
| 89 tests — all passing | ✅ Complete |
| OpenAPI docs at `/docs` | ✅ Complete |
| Static test token fallback for local dev | ✅ Complete |

---

## Next step — AI-Powered Hosting Account Health Report

The planned next feature is a new MCP tool (`get_hosting_health_report`) in the **MCP server** (`milesweb_mcp`) that answers:

> *"Analyze my MilesWeb hosting account and tell me if anything needs attention."*

The tool will combine multiple existing read-only Phase 2 operations to summarize:
- Website and subscription status
- Bandwidth and resource usage
- SSL certificate validity
- DNS status
- WordPress plugin / theme versions
- Backup availability
- Suspended or degraded services

**This mock backend requires zero changes to support the Health Report.** All 35 data sources it needs are already implemented and tested here.

The Health Report implementation is entirely in `milesweb_mcp/app/mcp_server.py` on Nitin's machine (deployed at `https://milesweb-mcp-b2vu.onrender.com/mcp`).

---

## MCP server integration reference

```python
import os
import httpx

def get_customer_profile(auth_context: dict) -> dict:
    """Example: how the MCP server calls this backend."""
    client_id = auth_context["client_id_whmcs"]  # from verified JWT — never from AI input
    response = httpx.get(
        "http://127.0.0.1:8000/api/v1/connector/customer",
        headers={"X-Connector-Key": os.environ["CONNECTOR_API_KEY"]},
        params={"clientId": client_id},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()["data"]
```

> [!WARNING]
> Never accept `clientId` as a free-form argument from the AI model. Always derive it from the already-verified authentication context. Never log the connector key or raw request headers.
