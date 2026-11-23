"""Read-only customer endpoints consumed by the authenticated MCP service."""

import hmac
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.config import Settings, get_settings
from app.customer_repository import CustomerRepository, repository

router = APIRouter(prefix="/api/v1/connector/customer", tags=["Customer connector"])


def require_connector_key(
    connector_key: Annotated[str | None, Header(alias="X-Connector-Key")] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """Authenticate the trusted MCP service without revealing key details."""
    if not settings.connector_api_key or not connector_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if not hmac.compare_digest(connector_key, settings.connector_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_repository() -> CustomerRepository:
    return repository


ClientId = Annotated[int, Query(..., alias="clientId", gt=0, description="Verified MilesWeb customer ID")]


def find_customer(client_id: ClientId, customer_repository: CustomerRepository) -> dict[str, Any]:
    customer = customer_repository.get_customer(client_id)
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.get("", dependencies=[Depends(require_connector_key)])
def get_customer(
    client_id: ClientId,
    customer_repository: CustomerRepository = Depends(get_repository),
) -> dict[str, Any]:
    """Return profile information for the customer identified by verified clientId."""
    customer = find_customer(client_id, customer_repository)
    return {
        "success": True,
        "data": {key: customer[key] for key in ("clientId", "name", "email", "status")},
    }


@router.get("/hosting-services", dependencies=[Depends(require_connector_key)])
def get_hosting_services(
    client_id: ClientId,
    customer_repository: CustomerRepository = Depends(get_repository),
) -> dict[str, Any]:
    """Return hosting services, including an empty list for customers without any."""
    customer = find_customer(client_id, customer_repository)
    return {"success": True, "data": customer["hostingServices"]}


@router.get("/domains", dependencies=[Depends(require_connector_key)])
def get_domains(
    client_id: ClientId,
    customer_repository: CustomerRepository = Depends(get_repository),
) -> dict[str, Any]:
    """Return registered domains, including an empty list for customers without any."""
    customer = find_customer(client_id, customer_repository)
    return {"success": True, "data": customer["domains"]}
