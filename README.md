# Enhance Mock Control Panel API & OAuth 2.1 Server (MilesWeb Edition)

Mock implementation of the **Enhance Control Panel API** and **OAuth 2.1 Authorization Server (compliant with MCP Authorization Specification 2026-07-28)** for organization domains, hosting plans, and AI assistant authentication (ChatGPT and Claude).  
Built with **FastAPI + Pydantic v2 + PyJWT + Uvicorn** for local testing, frontend integration, and MCP workflows.

---

## Live Render Deployment

- **Base URL:** `https://milesweb-mcp-server.onrender.com`
- **Metadata Discovery:** [https://milesweb-mcp-server.onrender.com/.well-known/oauth-authorization-server](https://milesweb-mcp-server.onrender.com/.well-known/oauth-authorization-server)
- **Interactive Swagger Docs:** [https://milesweb-mcp-server.onrender.com/docs](https://milesweb-mcp-server.onrender.com/docs)
- **Authorize Endpoint (Popup):** `https://milesweb-mcp-server.onrender.com/oauth/authorize`
- **Token Endpoint:** `https://milesweb-mcp-server.onrender.com/oauth/token`

---

## OAuth 2.1 Authorization Server (MCP Spec 2026-07-28)

| Method | Path | Description |
|---|---|---|
| `GET` | `/.well-known/oauth-authorization-server` | RFC 8414 OAuth 2.0 Authorization Server Metadata discovery |
| `POST` | `/oauth/register` | RFC 7591 Dynamic Client Registration endpoint (client credentials fallback) |
| `GET` | `/oauth/authorize` | Responsive browser popup for user login (Tab 1) & signup (Tab 2) |
| `POST` | `/oauth/authorize/submit` | Handles login/signup form submission & issues single-use auth code |
| `POST` | `/oauth/token` | Exchanges authorization code with PKCE (S256) for signed HS256 JWT access token |
| `GET` | `/api/auth/me` | Validates Bearer token and returns authenticated user claims |

### Pre-seeded Demo Credentials
- **Email:** `demo@milesweb.com`
- **Password:** `password123`
- **Org ID:** `c1a2b3d4-e5f6-7890-abcd-ef1234567890`

---

## Security & Gatepass (`org_id`)

The API enforces a single valid organization ID as a security gatepass:
- **`ORG_ID`**: `c1a2b3d4-e5f6-7890-abcd-ef1234567890`

Requests with any other `org_id` receive a `404 Not Found` (`{"code": "org_not_found"}`).

---

## Quick Start

```bash
cd enhance-mock-api

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Swagger Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints

### 1. Domains

| Method | Path | Description |
|---|---|---|
| `GET` | `/orgs/{org_id}/domains` | List domains registered to this organization (Enhance schema) |
| `POST` | `/orgs/{org_id}/domains/check` | Pre-flight check domain status (`available`, `in-use-same-org`, `in-use-other-org`, `prohibited`) |
| `POST` | `/orgs/{org_id}/domains/check/suggestions` | Client UI domain search: checks availability across multiple TLDs (`.com`, `.in`, `.co.in`, `.net`, `.org`) with dual-currency pricing & "1st year free" indicator |

#### GET `/orgs/{org_id}/domains`
Matches official Enhance schema:
```json
{
  "items": [
    {
      "id": "a1000000-0000-0000-0000-000000000001",
      "orgId": "c1a2b3d4-e5f6-7890-abcd-ef1234567890",
      "domain": "milesweb.com",
      "dkim": true,
      "spf": true,
      "cloudflareStatus": "Connected",
      "cloudflareTokenFriendlyName": "MilesWeb Primary CF Token"
    }
  ],
  "total": 5
}
```

#### POST `/orgs/{org_id}/domains/check` (Enhance-compatible Pre-flight)
- **Input Cleaning**: Strips protocols (`https://`), trailing slashes, and ports.
- **FQDN Syntax Check**: Requires at least one dot (host + TLD) and RFC-compliant labels. Missing TLD (e.g., `sweetcrumbs`) returns `HTTP 400 Bad Request`.
- **TLD Verification (IANA & ccTLDs)**: Validates against 1,436 official IANA root TLDs plus multi-part ccTLDs (`.co.in`, `.org.uk`, etc.). Non-existent or fake TLDs (e.g., `.lbcom`) return `status: "prohibited"`.
- **Reserved TLDs**: `.local`, `.test`, `.lan`, `.internal`, `localhost` return `status: "prohibited"`.
- **Existing Org Domain**: Returns `status: "in-use-same-org"` with associated `websiteId`.
- **Globally Taken Domain**: Returns `status: "in-use-other-org"`.

```json
// Example: Fake TLD check
// POST /orgs/{org_id}/domains/check -> {"domain": "soham.lbcom"}
{
  "status": "prohibited",
  "websiteId": null
}

// Example: Valid available domain
// POST /orgs/{org_id}/domains/check -> {"domain": "sweetcrumbs.in"}
{
  "status": "available",
  "websiteId": null
}

// Example: Existing domain in org
// POST /orgs/{org_id}/domains/check -> {"domain": "milesweb.com"}
{
  "status": "in-use-same-org",
  "websiteId": "01000000-0000-0000-0000-000000000001"
}
```

#### POST `/orgs/{org_id}/domains/check/suggestions` (Cart / UI Friendly)
Request:
```json
{ "domain": "dfdf" }
```
Response includes availability status, 1st year free flag, registration pricing in INR and USD, and registration duration choices (`[1, 2, 3, 5]` years).

---

### 2. Hosting Plans

| Method | Path | Description |
|---|---|---|
| `GET` | `/orgs/{org_id}/plans` | List organization hosting plans (Starter, Premium, Unlimited, Cloud Startup) |
| `GET` | `/orgs/{org_id}/plans/{plan_id}` | Get detailed plan info by ID (`1001`, `1002`, `1003`, `1004`) |
| `GET` | `/orgs/{org_id}/plans/pricing` | Dynamic plan pricing based on currency (`inr`, `usd`) and billing cycle (`monthly`, `annually`, `triennially`) |
| `GET` | `/orgs/{org_id}/plans/compare` | Full plan comparison matrix across Core, Platform, and Infrastructure categories |

#### Included Plans (MilesWeb)
1. **Starter** (`ID: 1001`): 1 Website, 10 GB NVMe, 1 Email, LiteSpeed, Free Domain (1yr)
2. **Premium** (`ID: 1002`): 25 Websites, 50 GB NVMe, 50 Emails, +2 extra months
3. **Unlimited - Best Value** (`ID: 1003`): Unlimited Websites, 75 GB NVMe, Unlimited Emails, 1 Node.js app
4. **Cloud Startup** (`ID: 1004`): 5 CPU, 5 GB RAM, 100 GB NVMe, 3 Node.js apps, OpenClaw AI ready

---

### 3. Pricing Matrix (INR & USD)

#### GET `/orgs/{org_id}/plans/pricing?currency=inr&billingCycle=annually`
Calculates:
- Discounted per-month price
- Total upfront price (12 or 36 months)
- 18% GST (for INR)
- Grand total (exact match to MilesWeb cart summary: ₹2,251.44 for Starter 12-month)

#### GET `/orgs/{org_id}/plans/pricing?currency=usd&billingCycle=triennially`
Calculates:
- Starter: $1.99/mo (Total: $71.64 for 36 months)
- Premium: $2.49/mo (Total: $89.64 for 36 months)
- Unlimited: $3.49/mo (Total: $125.64 for 36 months)
- Cloud Startup: $6.99/mo (Total: $251.64 for 36 months)

---

## Testing

Run the automated endpoint test suite:

```bash
# Test Enhance domains & plans
python test_endpoints.py

# Test OAuth 2.1 authorization server, PKCE S256, & JWT issuance
python test_oauth.py
```
