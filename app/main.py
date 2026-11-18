from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import domains, plans

app = FastAPI(
    title="Enhance Mock Control Panel API",
    description="Mock implementation of Enhance org domain & plan endpoints for local testing and MCP integration.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(domains.router)
app.include_router(plans.router)


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok"}
