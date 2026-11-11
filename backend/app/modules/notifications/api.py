"""In-app notification center (own notifications only)."""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update

from app.common.pagination import paginate
from app.core.authz import require_authenticated
from app.core.context import RequestContext
from app.core.errors import NotFound
from app.models.platform import InAppNotification

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _row(n: InAppNotification) -> dict:
    return {"id": str(n.id), "kind": n.kind, "title": n.title, "body": n.body, "link": n.link,
            "severity": n.severity, "read": n.read_at is not None,
            "read_at": n.read_at.isoformat() if n.read_at else None, "created_at": n.created_at.isoformat()}


@router.get("")
def list_notifications(page: int = 1, size: int = 30, unread_only: bool = False,
                       ctx: RequestContext = Depends(require_authenticated())):
    stmt = select(InAppNotification).where(InAppNotification.user_id == ctx.user_id)
    if unread_only:
        stmt = stmt.where(InAppNotification.read_at.is_(None))
    stmt = stmt.order_by(InAppNotification.read_at.is_not(None), InAppNotification.created_at.desc())
    rows, total, page, size = paginate(ctx.db, stmt, page, size)
    unread = ctx.db.execute(select(func.count()).select_from(InAppNotification).where(
        InAppNotification.user_id == ctx.user_id, InAppNotification.read_at.is_(None))).scalar()
    return {"items": [_row(n) for n in rows], "unread": unread, "total": total, "page": page, "size": size}


@router.get("/unread-count")
def unread_count(ctx: RequestContext = Depends(require_authenticated())):
    n = ctx.db.execute(select(func.count()).select_from(InAppNotification).where(
        InAppNotification.user_id == ctx.user_id, InAppNotification.read_at.is_(None))).scalar()
    return {"unread": n}


@router.post("/read-all")
def read_all(ctx: RequestContext = Depends(require_authenticated())):
    ctx.db.execute(update(InAppNotification).where(InAppNotification.user_id == ctx.user_id,
                                                   InAppNotification.read_at.is_(None))
                   .values(read_at=datetime.now(UTC)))
    ctx.commit()
    return {"message": "All notifications marked as read"}


@router.post("/{notification_id}/read")
def mark_read(notification_id: UUID, ctx: RequestContext = Depends(require_authenticated())):
    n = ctx.db.get(InAppNotification, notification_id)
    if n is None or n.user_id != ctx.user_id:
        raise NotFound("Notification")
    if n.read_at is None:
        n.read_at = datetime.now(UTC)
        ctx.commit()
    return {"message": "Notification marked as read"}
