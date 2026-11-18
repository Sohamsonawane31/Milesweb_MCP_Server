"""Domain schemas – aligned to Enhance API spec."""

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

CloudflareStatus = Literal["Connected", "Pending", "Disconnected"]


class DomainOut(BaseModel):
    """Matches Enhance GET /orgs/{org_id}/domains response item."""
    id: UUID
    orgId: UUID
    domain: str
    websiteId: Optional[UUID] = None
    dkim: bool = False
    spf: bool = False
    cloudflareStatus: CloudflareStatus = "Disconnected"
    cloudflareTokenFriendlyName: Optional[str] = None


class DomainsListing(BaseModel):
    items: List[DomainOut]
    total: int


class DomainCheckRequest(BaseModel):
    domain: str = Field(..., min_length=1, max_length=253, examples=["example.com"])


class DomainCheckResponse(BaseModel):
    """Enhance-compatible domain check response."""
    status: Literal["available", "in-use-same-org", "in-use-other-org", "prohibited"]
    websiteId: Optional[UUID] = None


class DomainSuggestionPricing(BaseModel):
    """Per-TLD pricing for a domain suggestion."""
    registration: float
    renewal: float


class DomainSuggestion(BaseModel):
    """A single TLD suggestion returned during domain check."""
    domain: str
    tld: str
    available: bool
    free_first_year: bool = False
    pricing: Optional[dict] = None  # {"inr": {...}, "usd": {...}}
    registration_periods: List[int] = [1, 2, 3, 5]


class DomainCheckWithSuggestionsResponse(BaseModel):
    """Extended response for domain check with TLD suggestions."""
    query: str
    base_name: str
    suggestions: List[DomainSuggestion]
