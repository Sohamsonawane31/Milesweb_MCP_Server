# MilesWeb read-only customer API

This FastAPI service provides a static, read-only customer lookup API for the MilesWeb MCP server. It retains the existing `/auth/login` mock route and adds an independently callable customer connector API. Customer records are fictional fixtures in `data/customers.json`; the application never writes them.

## Layout

```
app/
  config.py                 environment configuration
  customer_repository.py    read-only JSON database access
  routers/customer_router.py protected customer endpoints
data/customers.json         fictional customer and hosting fixtures
tests/                      API tests
```

## Configure and run

Python 3.11+ is recommended.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and set CONNECTOR_API_KEY to a long random secret.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`CONNECTOR_API_KEY` authenticates the trusted MCP service, not an end user. The MCP service must derive `clientId` from its verified login-token context; the shared key alone does not independently verify a customer's identity.

## API

All customer routes require `X-Connector-Key`. They only expose `GET`; other methods return `405 Method Not Allowed`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Unauthenticated health check |
| GET | `/api/v1/connector/customer?clientId=12345` | Customer profile |
| GET | `/api/v1/connector/customer/hosting-services?clientId=12345` | Hosting services |
| GET | `/api/v1/connector/customer/domains?clientId=12346` | Registered domains |

```powershell
curl.exe -H "X-Connector-Key: your-secret" "http://127.0.0.1:8000/api/v1/connector/customer?clientId=12345"
```

```json
{
  "success": true,
  "data": {
    "clientId": 12345,
    "name": "Rahul Sharma",
    "email": "rahul@example.com",
    "status": "Active"
  }
}
```

An unknown customer returns `404`; omitted, non-numeric, or non-positive `clientId` returns `422`; a missing or invalid connector key returns `401`. Customers with no hosting return `200` and `{"success": true, "data": []}`.

## MCP client example

Never accept the ID below as a free-form tool argument. Obtain it from the already verified authentication context, then pass it to this internal API.

```python
import os
import httpx

def customer_for_current_user(auth_context: dict) -> dict:
    client_id = auth_context["client_id_whmcs"]  # set by token verification
    response = httpx.get(
        "http://127.0.0.1:8000/api/v1/connector/customer",
        headers={"X-Connector-Key": os.environ["CONNECTOR_API_KEY"]},
        params={"clientId": client_id},
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()["data"]
```

Handle `httpx.HTTPStatusError` in the MCP tool to return a safe tool error. Do not log the connector key or full request headers.

## Phase 2 Enhance mock catalog

The Phase 2 mock also implements all 35 read-only `GET` operations from the supplied Enhance API catalog, including organizations, subscriptions, websites, domains/DNS/SSL, WordPress, backups, email, FTP, databases, Git, usage metrics, PHP settings, and activity history. Browse the complete endpoint list and schemas at `/docs`.

Each Phase 2 request must send both headers below:

```http
X-Connector-Key: <CONNECTOR_API_KEY>
Authorization: Bearer <verified-MCP-access-token>
```

For local mock testing, `PHASE2_TEST_TOKENS` maps an opaque bearer token to a fictional customer ID. The fixture contains Rahul (`12345`), Amit (`12346`), and Neha (`12348`). Every `org_id`, `website_id`, `subscription_id`, `domain_id`, and `app_id` is checked against that identity; another customer's resource returns `404`.

```powershell
curl.exe -H "X-Connector-Key: your-secret" -H "Authorization: Bearer mock-token-rahul" "http://127.0.0.1:8000/orgs/org-rahul-001/websites/site-rahul-001"
```

## Test

```powershell
pytest -q
```
