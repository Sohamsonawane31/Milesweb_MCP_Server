from fastapi import APIRouter

router = APIRouter(prefix="/orgs/{org_id}/plans", tags=["plans"])


@router.get("")
async def list_plans():
    return [
        {"id": 1001, "name": "Starter"},
        {"id": 1002, "name": "Premium"},
        {"id": 1003, "name": "Unlimited"},
        {"id": 1004, "name": "Cloud Startup"},
    ]


@router.get("/{plan_id}")
async def get_plan(plan_id: int):
    return {"id": plan_id, "name": f"Plan {plan_id}"}