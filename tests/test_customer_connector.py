import json
from pathlib import Path

import pytest


CUSTOMER_PATH = Path(__file__).resolve().parents[1] / "data" / "customers.json"


def test_customer_lookup_with_valid_key(client, auth_headers):
    response = client.get("/api/v1/connector/customer?clientId=12345", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"clientId": 12345, "name": "Rahul Sharma", "email": "rahul@example.com", "status": "Active"}}


@pytest.mark.parametrize("headers", [{}, {"X-Connector-Key": "wrong-key"}])
def test_customer_lookup_rejects_missing_or_wrong_key(client, headers):
    assert client.get("/api/v1/connector/customer?clientId=12345", headers=headers).status_code == 401


def test_hosting_services_for_customer_with_services(client, auth_headers):
    response = client.get("/api/v1/connector/customer/hosting-services?clientId=12345", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"][0]["hostingPlan"] == "Business Hosting"


def test_hosting_services_for_customer_without_services(client, auth_headers):
    response = client.get("/api/v1/connector/customer/hosting-services?clientId=12347", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": []}


def test_customer_can_have_multiple_hosting_services(client, auth_headers):
    response = client.get("/api/v1/connector/customer/hosting-services?clientId=12348", headers=auth_headers)
    assert response.status_code == 200
    assert [service["serviceId"] for service in response.json()["data"]] == [1003, 1004]


def test_domains_for_customer_with_one_domain(client, auth_headers):
    response = client.get("/api/v1/connector/customer/domains?clientId=12345", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] == [{"domainId": 2001, "domainName": "rahulcloud.example", "status": "Active", "registrationDate": "2025-12-31", "expiryDate": "2027-12-31", "autoRenew": True}]


def test_domains_for_customer_with_multiple_domains(client, auth_headers):
    response = client.get("/api/v1/connector/customer/domains?clientId=12346", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 3
    assert response.json()["data"][1]["status"] == "Pending"


def test_domains_for_customer_without_domains(client, auth_headers):
    response = client.get("/api/v1/connector/customer/domains?clientId=12347", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": []}


def test_domains_without_hosting_are_returned(client, auth_headers):
    response = client.get("/api/v1/connector/customer/domains?clientId=12349", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2
    assert client.get("/api/v1/connector/customer/hosting-services?clientId=12349", headers=auth_headers).json()["data"] == []


def test_unknown_customer_returns_404(client, auth_headers):
    assert client.get("/api/v1/connector/customer?clientId=99999", headers=auth_headers).status_code == 404


@pytest.mark.parametrize("url", ["/api/v1/connector/customer", "/api/v1/connector/customer?clientId=abc", "/api/v1/connector/customer?clientId=0"])
def test_invalid_client_id_returns_422(client, auth_headers, url):
    assert client.get(url, headers=auth_headers).status_code == 422


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
@pytest.mark.parametrize("path", ["/api/v1/connector/customer?clientId=12345", "/api/v1/connector/customer/hosting-services?clientId=12345", "/api/v1/connector/customer/domains?clientId=12345"])
def test_customer_routes_are_read_only(client, auth_headers, method, path):
    assert getattr(client, method)(path, headers=auth_headers).status_code == 405


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_requests_do_not_modify_fixture(client, auth_headers):
    before = json.loads(CUSTOMER_PATH.read_text(encoding="utf-8"))
    client.get("/api/v1/connector/customer?clientId=12345", headers=auth_headers)
    client.get("/api/v1/connector/customer/hosting-services?clientId=12345", headers=auth_headers)
    client.get("/api/v1/connector/customer/domains?clientId=12345", headers=auth_headers)
    assert json.loads(CUSTOMER_PATH.read_text(encoding="utf-8")) == before


def test_authenticated_lookup_only_returns_requested_verified_client(client, auth_headers):
    """MCP supplies this value from its verified token context, never a tool argument."""
    response = client.get("/api/v1/connector/customer?clientId=12346", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["clientId"] == 12346
    assert response.json()["data"]["email"] == "amit@example.com"
