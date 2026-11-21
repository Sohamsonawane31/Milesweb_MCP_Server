from fastapi import APIRouter

router = APIRouter(prefix="/orgs/{org_id}/domains", tags=["domains"])


@router.get("")
async def list_domains():
    return {"items": [], "total": 0}


@router.post("/check")
async def check_domain():
    return {"status": "available", "websiteId": None}


@router.post("/check/suggestions")
async def domain_suggestions():
    return {"items": [], "total": 0}