"""Dashboard aggregation route."""
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.core.authz import require
from app.core.context import RequestContext
from app.core.errors import ValidationFailed
from app.modules.dashboard import service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(date_from: date | None = None, date_to: date | None = None,
            from_: date | None = Query(None, alias="from"), to: date | None = Query(None),
            ctx: RequestContext = Depends(require("dashboard:read"))):
    date_from, date_to = date_from or from_, date_to or to
    if date_from and date_to and date_from > date_to:
        raise ValidationFailed("The start date must be before the end date.",
                               [{"field": "date_from", "message": "After date_to"}])
    return service.summary(ctx, date_from, date_to)
