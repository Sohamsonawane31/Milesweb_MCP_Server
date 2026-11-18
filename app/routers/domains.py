"""Domain router – GET /orgs/{org_id}/domains & POST /orgs/{org_id}/domains/check"""

import re
from typing import Literal, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.data.iana_tlds import ALL_VALID_TLDS, IANA_TLDS, MULTI_PART_TLDS
from app.data.mock_store import (
    DOMAIN_REGISTRATION_PERIODS,
    DOMAIN_SUGGESTION_TLDS,
    DOMAIN_TLD_PRICING,
    GLOBALLY_TAKEN_DOMAINS,
    MOCK_DOMAINS,
    REGISTERED_DOMAINS_DB,
    VALID_ORGS,
)
from app.schemas.domain import (
    DomainCheckRequest,
    DomainCheckResponse,
    DomainCheckWithSuggestionsResponse,
    DomainSuggestion,
    DomainsListing,
)

router = APIRouter(prefix="/orgs/{org_id}/domains", tags=["Domains"])

# Regex for a valid label: 1 to 63 alphanumeric or hyphen (cannot start or end with hyphen)
LABEL_REGEX = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")

# Reserved / special-use TLDs that cannot be used on the public web (RFC 2606, RFC 6761)
RESERVED_PROHIBITED_TLDS = frozenset([
    "local",
    "localhost",
    "internal",
    "lan",
    "home",
    "corp",
    "test",
    "example",
    "invalid",
    "onion",
    "arpa",
    "intranet",
    "priv",
])

# Prohibited host substrings or IP patterns
PROHIBITED_HOST_PATTERNS = ("localhost", "0.0.0.0", "127.0.0.1")


def _validate_org(org_id: UUID) -> None:
    if org_id not in VALID_ORGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "org_not_found", "detail": f"Organization {org_id} not found"},
        )


def _clean_domain_input(raw: str) -> str:
    """
    Cleans domain input by stripping protocols, ports, trailing paths,
    whitespace, and trailing dots.
    Examples:
      'https://www.sweetcrumbs.in/' -> 'www.sweetcrumbs.in'
      'http://nitin.com:80/path'    -> 'nitin.com'
      '  soham.lbcom.  '            -> 'soham.lbcom'
    """
    cleaned = raw.strip().lower()
    if "://" in cleaned:
        cleaned = cleaned.split("://", 1)[1]
    for delimiter in ("/", "?", "#", ":"):
        if delimiter in cleaned:
            cleaned = cleaned.split(delimiter, 1)[0]
    return cleaned.rstrip(".")


def _extract_tld_and_sld(domain: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts the recognized TLD (or ccSLD) and the base SLD from a domain.
    Checks multi-part ccTLDs first (e.g. 'co.in', 'com.au', 'org.uk'),
    then single-part IANA TLDs (e.g. 'com', 'in', 'org').

    Returns:
        (tld, sld) if recognized, or (None, parts[0]) if unrecognized TLD.
    """
    parts = domain.split(".")
    if len(parts) < 2:
        return None, domain

    # Check multi-part ccSLD first (e.g., 'sweetcrumbs.co.in' -> tld='co.in', sld='sweetcrumbs')
    if len(parts) >= 3:
        two_part = f"{parts[-2]}.{parts[-1]}"
        if two_part in MULTI_PART_TLDS:
            return two_part, parts[-3]

    # Check single-part IANA TLD (e.g., 'sweetcrumbs.in' -> tld='in', sld='sweetcrumbs')
    one_part = parts[-1]
    if one_part in IANA_TLDS:
        return one_part, parts[-2]

    # Unrecognized / fake TLD (e.g. 'soham.lbcom' -> tld=None)
    return None, parts[0]


def _validate_domain_syntax(domain: str, raw_input: str) -> None:
    """
    Validates domain syntax according to RFC 1035 / 1123.
    Requires at least one dot (host + TLD), max 253 chars, and valid labels.
    Raises HTTP 400 if syntax is malformed.
    """
    if not domain or len(domain) > 253:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_input",
                "detail": f"Domain name length must be between 1 and 253 characters. Received: '{raw_input}'.",
            },
        )

    # Must contain at least one dot to have a TLD
    if "." not in domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_input",
                "detail": (
                    f"Domain '{raw_input}' is missing a top-level domain extension (TLD). "
                    "A fully-qualified domain name is required (e.g., 'sweetcrumbs.in' or 'nitin.com')."
                ),
            },
        )

    parts = domain.split(".")
    for part in parts:
        if not part or not LABEL_REGEX.match(part):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_input",
                    "detail": (
                        f"Domain '{raw_input}' contains invalid label '{part}'. "
                        "Labels must be 1-63 alphanumeric characters and cannot start or end with a hyphen."
                    ),
                },
            )


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


# ── GET /orgs/{org_id}/domains/tlds ───────────────────────────
@router.get("/tlds")
async def list_supported_tlds(
    org_id: UUID = Path(..., description="Organization UUID"),
    search: Optional[str] = Query(None, description="Filter TLDs by prefix/substring, e.g. 'com', 'in', 'ai'"),
    limit: int = Query(50, ge=1, le=500, description="Max TLDs to return"),
):
    """
    Returns verified hostable TLDs and recognized multi-part ccTLDs.
    Used by client UI for domain search, autocomplete, and extension dropdowns.
    """
    _validate_org(org_id)

    priority_order = [".com", ".in", ".co.in", ".net", ".org", ".io", ".ai", ".dev", ".app"]
    all_tlds = [f".{t}" for t in sorted(ALL_VALID_TLDS)]

    if search:
        term = search.strip().lower().lstrip(".")
        all_tlds = [t for t in all_tlds if term in t.lstrip(".")]

    reordered = [t for t in priority_order if t in all_tlds] + [t for t in all_tlds if t not in priority_order]

    return {
        "total": len(reordered),
        "count": len(reordered[:limit]),
        "tlds": reordered[:limit],
    }


# ── POST /orgs/{org_id}/domains/check (Enhance-compatible) ───
@router.post("/check", response_model=DomainCheckResponse)
async def check_domain(
    payload: DomainCheckRequest,
    org_id: UUID = Path(..., description="Organization UUID"),
):
    """
    Check if a domain can be created in the organization (Enhance-compatible).

    Enhance returns one of four statuses:
    - 'available': Domain is valid, exists on public DNS/IANA, and is free to add.
    - 'in-use-same-org': Domain is already bound to a website in this org (returns websiteId).
    - 'in-use-other-org': Domain is in use by another tenant in the cluster.
    - 'prohibited': Domain cannot be added because:
        * TLD does not exist / is fake (e.g. '.lbcom')
        * TLD is reserved / private (e.g. '.local', '.test', '.internal', '.lan')
        * Domain contains prohibited hostnames (e.g. 'localhost', '0.0.0.0')

    Raises HTTP 400 if domain syntax is invalid or missing a TLD.
    """
    _validate_org(org_id)

    raw = payload.domain
    cleaned = _clean_domain_input(raw)

    # 1. Validate domain syntax (FQDN format & dot requirement) -> 400 if invalid
    _validate_domain_syntax(cleaned, raw)

    # 2. Extract and validate TLD
    tld, _ = _extract_tld_and_sld(cleaned)
    last_segment = cleaned.split(".")[-1]

    # If the TLD is in reserved/prohibited private namespaces -> prohibited
    if last_segment in RESERVED_PROHIBITED_TLDS:
        return DomainCheckResponse(status="prohibited", websiteId=None)

    # If the TLD does not exist in the official IANA/ccTLD registry -> prohibited
    if tld is None:
        return DomainCheckResponse(status="prohibited", websiteId=None)

    # 3. Check prohibited hostnames / IP addresses -> prohibited
    if any(p in cleaned for p in PROHIBITED_HOST_PATTERNS):
        return DomainCheckResponse(status="prohibited", websiteId=None)

    # 4. Check if domain is already in this organization
    for d in MOCK_DOMAINS:
        if d["domain"].lower() == cleaned and d["orgId"] == org_id:
            return DomainCheckResponse(
                status="in-use-same-org",
                websiteId=d.get("websiteId"),
            )

    # 5. Check if domain is in use by another tenant or globally taken
    if cleaned in GLOBALLY_TAKEN_DOMAINS or any(
        d["domain"].lower() == cleaned for d in MOCK_DOMAINS
    ):
        return DomainCheckResponse(status="in-use-other-org", websiteId=None)

    # 6. Valid, real TLD, not taken -> available to be created
    return DomainCheckResponse(status="available", websiteId=None)


# ── POST /orgs/{org_id}/domains/check/suggestions ────────────
@router.post("/check/suggestions", response_model=DomainCheckWithSuggestionsResponse)
async def check_domain_with_suggestions(
    payload: DomainCheckRequest,
    org_id: UUID = Path(..., description="Organization UUID"),
):
    """
    Extended domain search returning TLD suggestions with availability and pricing.
    Designed for the client checkout / cart UI (MilesWeb style).
    Accepts both bare brand names (e.g., 'sweetcrumbs', 'dfdf') and full domains (e.g., 'soham.lbcom').
    """
    _validate_org(org_id)

    cleaned = _clean_domain_input(payload.domain)
    # Extract base SLD name (e.g. 'soham.lbcom' -> 'soham', 'sweetcrumbs' -> 'sweetcrumbs')
    parts = cleaned.split(".")
    base_name = parts[0] if parts else cleaned

    suggestions = []
    registered_tlds = REGISTERED_DOMAINS_DB.get(base_name, set())

    for tld in DOMAIN_SUGGESTION_TLDS:
        full_domain = f"{base_name}{tld}"
        is_available = tld not in registered_tlds

        # Check globally taken
        if full_domain in GLOBALLY_TAKEN_DOMAINS:
            is_available = False

        # Check existing org domains
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
        query=payload.domain,
        base_name=base_name,
        suggestions=suggestions,
    )
