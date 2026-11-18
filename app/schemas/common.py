from typing import Literal, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str = Field(..., examples=["not_found"])
    detail: Optional[str] = Field(None, examples=["Resource not found"])


class PaginationQuery(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=200)
    sort_by: Optional[str] = None
    sort_order: Literal["asc", "desc"] = "asc"
