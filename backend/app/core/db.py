"""Database engines and sessions.

The API and workers connect as role dapro_app (no BYPASSRLS). Each transaction binds
app.tenant_id so PostgreSQL row-level security isolates tenants (LLD sections 2 and 4).
"""
from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

engine = create_engine(_settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
owner_engine = create_engine(_settings.database_owner_url, pool_pre_ping=True, pool_size=2)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
OwnerSessionLocal = sessionmaker(bind=owner_engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _bind_tenant(session, transaction, connection):
    tenant_id = session.info.get("tenant_id")
    if tenant_id:
        connection.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})


def bind_tenant(session: Session, tenant_id) -> None:
    """Bind tenant for the current and every following transaction of this session."""
    session.info["tenant_id"] = str(tenant_id)
    if session.in_transaction():
        session.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
