"""Shared pydantic helpers."""
from pydantic import BaseModel, ConfigDict


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Msg(BaseModel):
    message: str


class Freshness(BaseModel):
    """Every financial or personal value carries its source and as-of (RD 4.3, FR-REP-10)."""
    source: str
    as_of: str | None
    sync_state: str
