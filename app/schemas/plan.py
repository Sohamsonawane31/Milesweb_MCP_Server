"""Plan schemas – aligned to Enhance API spec + MilesWeb display data."""

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

PlanType = Literal["shared", "dedicated"]


class PlanResource(BaseModel):
    name: str
    total: int = 0


class PlanAllowance(BaseModel):
    name: str


class PlanSelection(BaseModel):
    name: str
    value: str


class CgroupLimits(BaseModel):
    nproc: int = 0
    memoryLimit: int = 0
    iops: int = 0
    ioBandwidth: int = 0
    virtualCpus: int = 0
    swapLimit: int = 0


class FsQuotaLimit(BaseModel):
    totalAvailable: int = 0
    inodesAvailable: int = 0


class PlanDisplayInfo(BaseModel):
    """Extra fields for client-side rendering (non-Enhance)."""
    tagline: str = ""
    highlight: Optional[str] = None  # e.g. "Best Value"
    features: List[str] = []
    features_full: List[str] = []
    nodejs_apps: int = 0
    openclaw_ready: bool = False


class PlanOut(BaseModel):
    """Matches Enhance GET /orgs/{org_id}/plans response item."""
    id: int
    name: str
    orgId: UUID
    resources: List[PlanResource] = []
    allowances: List[PlanAllowance] = []
    selections: List[PlanSelection] = []
    subscriptionsCount: int = 0
    serverGroupIds: List[str] = []
    allowServerGroupSelection: bool = True
    createdAt: str
    planType: PlanType = "shared"
    cgroupLimits: Optional[CgroupLimits] = None
    fsQuotaLimit: Optional[FsQuotaLimit] = None
    allowedPhpVersions: List[str] = []
    defaultPhpVersion: str = "php82"
    redisAllowed: bool = False
    preinstallWordpressTheme: Optional[str] = None
    persistentAppsAllowed: bool = False
    allowedApps: List[str] = []

    # Non-Enhance fields for client UI
    display: Optional[PlanDisplayInfo] = Field(None, alias="_display")

    class Config:
        populate_by_name = True


class PlansListing(BaseModel):
    items: List[PlanOut]
    total: int


# ---------------------------------------------------------------------------
# Pricing schemas
# ---------------------------------------------------------------------------

class CyclePricing(BaseModel):
    """Pricing for one billing cycle in one currency."""
    original: float
    discounted: float
    renewal: float


class PlanPricingOut(BaseModel):
    """Full pricing for a single plan across all billing cycles."""
    plan_id: int
    plan_name: str
    currency: str
    billing_cycle: str
    months: int
    price_per_month: CyclePricing
    total_price: float          # discounted * months
    total_original: float       # original * months
    savings: float              # total_original - total_price
    discount_pct: int
    extra_months: int
    free_domain: bool
    tax: Optional[Dict[str, Any]] = None  # {"name": "GST", "rate": 18.0, "amount": ...}
    grand_total: Optional[float] = None   # total_price + tax amount


class AllPlansPricingOut(BaseModel):
    """Pricing for all plans in a given currency & billing cycle."""
    currency: str
    billing_cycle: str
    plans: List[PlanPricingOut]
    money_back_days: int = 30
