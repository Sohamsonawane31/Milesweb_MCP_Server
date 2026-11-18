"""Plans router – GET /orgs/{org_id}/plans, GET /orgs/{org_id}/plans/{plan_id}, GET pricing"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.data.mock_store import (
    BILLING_CYCLE_MONTHS,
    MOCK_PLANS,
    MONEY_BACK_DAYS,
    PLAN_COMPARISON,
    PLAN_PRICING,
    TAX_RATES,
    VALID_ORGS,
)
from app.schemas.plan import (
    AllPlansPricingOut,
    PlanOut,
    PlanPricingOut,
    PlansListing,
)

router = APIRouter(prefix="/orgs/{org_id}/plans", tags=["Plans"])


def _validate_org(org_id: UUID) -> None:
    if org_id not in VALID_ORGS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "org_not_found", "detail": f"Organization {org_id} not found"},
        )


# ── GET /orgs/{org_id}/plans ─────────────────────────────────
@router.get("", response_model=PlansListing)
async def list_org_plans(
    org_id: UUID = Path(..., description="Organization UUID"),
    sort_by: Literal["name"] = Query("name", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query("asc", alias="sortOrder"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Returns the organization's plans."""
    _validate_org(org_id)

    filtered = [p for p in MOCK_PLANS if str(p["orgId"]) == str(org_id)]

    reverse = sort_order == "desc"
    filtered.sort(key=lambda item: item.get(sort_by, ""), reverse=reverse)

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return PlansListing(items=paginated, total=total)


# ── GET /orgs/{org_id}/plans/pricing ─────────────────────────
# MUST be before /{plan_id} to avoid route conflict
@router.get("/pricing", response_model=AllPlansPricingOut)
async def get_plans_pricing(
    org_id: UUID = Path(..., description="Organization UUID"),
    currency: Literal["inr", "usd"] = Query("inr", description="Currency: inr or usd"),
    billing_cycle: Literal["monthly", "annually", "triennially"] = Query(
        "triennially", alias="billingCycle", description="Billing cycle"
    ),
):
    """
    Returns pricing for all plans in the given currency & billing cycle.
    Includes original price, discounted price, savings, tax, and grand total.
    """
    _validate_org(org_id)

    org_plans = [p for p in MOCK_PLANS if str(p["orgId"]) == str(org_id)]
    months = BILLING_CYCLE_MONTHS[billing_cycle]
    tax_info = TAX_RATES.get(currency, {"name": "Tax", "rate": 0.0})
    results = []

    for plan in org_plans:
        plan_id = plan["id"]
        pricing = PLAN_PRICING.get(plan_id)
        if not pricing:
            continue

        currency_pricing = pricing.get(currency, {}).get(billing_cycle)
        if not currency_pricing:
            continue

        total_price = round(currency_pricing["discounted"] * months, 2)
        total_original = round(currency_pricing["original"] * months, 2)
        savings = round(total_original - total_price, 2)

        tax_amount = round(total_price * tax_info["rate"] / 100, 2)
        grand_total = round(total_price + tax_amount, 2)

        results.append(
            PlanPricingOut(
                plan_id=plan_id,
                plan_name=plan["name"],
                currency=currency,
                billing_cycle=billing_cycle,
                months=months,
                price_per_month={
                    "original": currency_pricing["original"],
                    "discounted": currency_pricing["discounted"],
                    "renewal": currency_pricing["renewal"],
                },
                total_price=total_price,
                total_original=total_original,
                savings=savings,
                discount_pct=pricing["discount_pct"][billing_cycle],
                extra_months=pricing["extra_months"][billing_cycle],
                free_domain=pricing["free_domain"][billing_cycle],
                tax={"name": tax_info["name"], "rate": tax_info["rate"], "amount": tax_amount},
                grand_total=grand_total,
            )
        )

    return AllPlansPricingOut(
        currency=currency,
        billing_cycle=billing_cycle,
        plans=results,
        money_back_days=MONEY_BACK_DAYS,
    )


# ── GET /orgs/{org_id}/plans/compare ─────────────────────────
# MUST be before /{plan_id} to avoid route conflict
@router.get("/compare")
async def get_plan_comparison(
    org_id: UUID = Path(..., description="Organization UUID"),
):
    """Returns the plan comparison table data for the client-side grid."""
    _validate_org(org_id)
    return PLAN_COMPARISON


# ── GET /orgs/{org_id}/plans/{plan_id} ───────────────────────
@router.get("/{plan_id}", response_model=PlanOut)
async def get_org_plan(
    org_id: UUID = Path(..., description="Organization UUID"),
    plan_id: int = Path(..., ge=1, description="Numeric Plan ID"),
):
    """Returns info on a single plan."""
    _validate_org(org_id)

    for plan in MOCK_PLANS:
        if str(plan["orgId"]) == str(org_id) and plan["id"] == plan_id:
            return plan

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "plan_not_found",
            "detail": f"Plan {plan_id} not found in organization {org_id}",
        },
    )
