"""In-app notification center entries."""
from sqlalchemy.orm import Session


def notify(db: Session, tenant_id, user_id, kind: str, title: str, body: str | None = None,
           link: str | None = None, severity: str = "INFO") -> None:
    from app.models.platform import InAppNotification

    if user_id is None:
        return
    db.add(InAppNotification(tenant_id=tenant_id, user_id=user_id, kind=kind, title=title, body=body,
                             link=link, severity=severity))
