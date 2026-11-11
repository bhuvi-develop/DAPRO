"""Global search route."""
from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.search import service

router = APIRouter(tags=["search"])


@router.get("/search")
def search(q: str = "", ctx: RequestContext = Depends(require("dashboard:read"))):
    return service.search(ctx, q)
