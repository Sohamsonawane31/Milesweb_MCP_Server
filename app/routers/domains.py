"""Domain router – GET /orgs/{org_id}/domains & POST /orgs/{org_id}/domains/check"""

import re
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.data.mock_store import (
    DOMAIN_SUGGESTION_TLDS,
    DOMAIN_TLD_PRICING,
    GLOBALLY_TAKEN_DOMAINS,
    MOCK_DOMAINS,
    REGISTERED_DOMAINS_DB,
    VALID_ORGS,
    DOMAIN_REGISTRATION_PERIODS,
)
from app.schemas.domain import (
    DomainCheckRequest,
    DomainCheckResponse,
    DomainCheckWithSuggestionsResponse,
    DomainSuggestion,
    DomainsListing,
)

router = APIRouter(prefix="/orgs/{org_id}/domains", tags=["Domains"])

DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
)


def _validate_org(org_id: UUID) -> None:
    if org_id not in VALID_ORGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "org_not_found", "detail": f"Organization {org_id} not found"},
        )


def _extract_base_name(domain_input: str) -> str:
    """Extract base name from input: 'example.com' -> 'example', 'example' -> 'example'."""
    parts = domain_input.split(".")
    return parts[0]


# ── GET /orgs/{org_id}/domains ───────────────────────────────
@router.get("", response_model=DomainsListing)
async def list_org_domains(
    org_id: UUID = Path(..., description="Organization UUID"),
    sort_by: Literal["domain"] = Query("domain", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query("asc", alias="sortOrder"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Lists the domains belonging to this organization."""
    _validate_org(org_id)

    filtered = [d for d in MOCK_DOMAINS if d["orgId"] == org_id]

    reverse = sort_order == "desc"
    filtered.sort(key=lambda item: item.get(sort_by, ""), reverse=reverse)

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return DomainsListing(items=paginated, total=total)


# ── POST /orgs/{org_id}/domains/check (Enhance-compatible) ───
@router.post("/check", response_model=DomainCheckResponse)
async def check_domain(
    payload: DomainCheckRequest,
    org_id: UUID = Path(..., description="Organization UUID"),
):
    """Check if a domain can be created (Enhance-compatible response)."""
    _validate_org(org_id)

    normalized = payload.domain.strip().lower().rstrip(".")

    # Check if domain exists in this org
    for d in MOCK_DOMAINS:
        if d["domain"].lower() == normalized and d["orgId"] == org_id:
            return DomainCheckResponse(
                status="in-use-same-org",
                websiteId=None,
            )

    # Check if domain is globally taken or in another org
    if normalized in GLOBALLY_TAKEN_DOMAINS or any(
        d["domain"].lower() == normalized for d in MOCK_DOMAINS
    ):
        return DomainCheckResponse(status="in-use-other-org")

    # Check prohibited patterns
    prohibited_patterns = ["localhost", "0.0.0.0", "127.0.0.1"]
    if any(p in normalized for p in prohibited_patterns):
        return DomainCheckResponse(status="prohibited")

    return DomainCheckResponse(status="available")


# ── POST /orgs/{org_id}/domains/check/suggestions ────────────
@router.post("/check/suggestions", response_model=DomainCheckWithSuggestionsResponse)
async def check_domain_with_suggestions(
    payload: DomainCheckRequest,
    org_id: UUID = Path(..., description="Organization UUID"),
):
    """
    Extended domain check that returns TLD suggestions with pricing.
    This is used by the cart/checkout flow to show domain availability
    across multiple TLDs with registration pricing.
    """
    _validate_org(org_id)

    raw = payload.domain.strip().lower().rstrip(".")
    base_name = _extract_base_name(raw)
    suggestions = []

    # Look up which TLDs are already registered for this base name
    registered_tlds = REGISTERED_DOMAINS_DB.get(base_name, set())

    for tld in DOMAIN_SUGGESTION_TLDS:
        full_domain = f"{base_name}{tld}"
        is_available = tld not in registered_tlds

        # Also check globally taken
        if full_domain in GLOBALLY_TAKEN_DOMAINS:
            is_available = False

        # Also check our org's own domains
        if any(d["domain"].lower() == full_domain for d in MOCK_DOMAINS):
            is_available = False

        tld_pricing = DOMAIN_TLD_PRICING.get(tld)
        pricing_data = None
        free_first_year = False
        if tld_pricing:
            pricing_data = {
                "inr": tld_pricing["inr"],
                "usd": tld_pricing["usd"],
            }
            free_first_year = tld_pricing.get("free_with_plan", False)

        suggestions.append(
            DomainSuggestion(
                domain=full_domain,
                tld=tld,
                available=is_available,
                free_first_year=free_first_year,
                pricing=pricing_data,
                registration_periods=DOMAIN_REGISTRATION_PERIODS,
            )
        )

    return DomainCheckWithSuggestionsResponse(
        query=raw,
        base_name=base_name,
        suggestions=suggestions,
    )
