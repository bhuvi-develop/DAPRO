"""Foundation controls: auth, route permission coverage, RLS, append-only audit, DPD engine, sync idempotency."""
import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError

from app.models.loans import LoanAccount, RepaymentTransaction, ScheduleInstalment


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["database"] is True


def test_login_and_me(client, auth):
    r = client.get("/api/v1/auth/me", headers=auth("loan_ops"))
    assert r.status_code == 200
    me = r.json()
    assert me["roles"] == ["BANK_LOAN_OPS"] and "loan:financial" in me["permissions"]
    assert me["tenant"]["environment"] == "DEMO"


def test_bad_password_rejected_and_audited(client, owner_db):
    r = client.post("/api/v1/auth/login", json={"email": "ravi.ops@anb.demo", "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "UNAUTHENTICATED"
    n = owner_db.execute(text("select count(*) from audit_events where action = :a and outcome = :o"),
                         {"a": "auth.login", "o": "FAILURE"}).scalar()
    assert n >= 1


def test_unauthenticated_request_rejected(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["next_step"]


def test_every_route_declares_permission():
    """LLD section 4: the build fails if any route lacks a require(...) dependency."""
    from fastapi.routing import APIRoute

    from app.main import app
    from app.modules.auth.api import PUBLIC_PATHS

    missing = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or route.path in PUBLIC_PATHS or route.path in ("/api/v1/health", "/metrics"):
            continue
        deps = [d.call for d in route.dependant.dependencies]
        if not any(hasattr(c, "__dapro_permission__") for c in deps):
            missing.append(f"{','.join(route.methods)} {route.path}")
    assert not missing, f"Routes without permission: {missing}"


def _app_engine():
    return create_engine(os.environ["DAPRO_DATABASE_URL"])


def _tenant(db, code):
    return db.execute(text("select id from tenants where code = :c"), {"c": code}).scalar()


def test_rls_isolates_tenants(owner_db):
    demo, iso = _tenant(owner_db, "DEMO"), _tenant(owner_db, "ISOTEST")
    eng = _app_engine()
    with eng.connect() as c:
        assert c.execute(text("select count(*) from students")).scalar() == 0
        c.execute(text("select set_config(:k, :t, false)"), {"k": "app.tenant_id", "t": str(iso)})
        assert c.execute(text("select count(*) from students")).scalar() == 3
        assert c.execute(text("select count(*) from students where tenant_id = :d"), {"d": str(demo)}).scalar() == 0
        with pytest.raises(DBAPIError):
            c.execute(text("insert into ref_counters (id, tenant_id, name, value) "
                           "values (gen_random_uuid(), :d, :n, 1)"), {"d": str(demo), "n": "x"})
    eng.dispose()


@pytest.mark.parametrize("table", ["audit_events", "repayment_transactions", "loan_snapshots"])
def test_append_only_tables_reject_delete_by_app_role(owner_db, table):
    eng = _app_engine()
    with eng.connect() as c:
        c.execute(text("select set_config(:k, :t, false)"), {"k": "app.tenant_id", "t": str(_tenant(owner_db, "DEMO"))})
        with pytest.raises(DBAPIError):
            c.execute(text(f"delete from {table}"))
    eng.dispose()


def test_audit_trigger_blocks_even_owner(owner_db):
    with pytest.raises(DBAPIError):
        owner_db.execute(text("update audit_events set outcome = :o"), {"o": "X"})


def test_audit_chain_verifies(owner_db):
    from app.core.audit import verify_chain

    res = verify_chain(owner_db, _tenant(owner_db, "DEMO"))
    assert res["ok"] and res["events_checked"] > 10


def test_dpd_classification_rules():
    from app.modules.repayments.engine import bucket_for, classify_instalment

    today = date(2026, 11, 20)

    def mk(due, amt, alloc, bs=None):
        return ScheduleInstalment(due_date=due, amount_due=Decimal(amt), bank_allocated_amount=alloc, bank_status=bs)

    assert classify_instalment(mk(date(2026, 12, 5), "100", Decimal("0")), today, 0) == ("UPCOMING", None)
    assert classify_instalment(mk(date(2026, 11, 5), "100", Decimal("100")), today, 0) == ("PAID", 0)
    assert classify_instalment(mk(date(2026, 11, 5), "100", Decimal("60")), today, 0) == ("PARTIALLY_PAID", 15)
    assert classify_instalment(mk(date(2026, 11, 5), "100", Decimal("0")), today, 0) == ("OVERDUE", 15)
    assert classify_instalment(mk(date(2026, 11, 5), "100", None), today, 0) == ("UNKNOWN", None)
    assert classify_instalment(mk(date(2026, 11, 5), "100", Decimal("0")), today, 20) == ("IN_GRACE", 0)
    assert classify_instalment(mk(date(2026, 11, 5), "100", Decimal("0"), "DEFERRED"), today, 0)[0] == "DEFERRED"
    b = [{"code": "C", "min": 0, "max": 0}, {"code": "E", "min": 1, "max": 30}, {"code": "X", "min": 31, "max": None}]
    assert bucket_for(15, b) == "E" and bucket_for(400, b) == "X" and bucket_for(None, b) is None


def test_duplicate_sync_is_idempotent(owner_db):
    """AC-04: replaying the bank feed creates no duplicate transactions."""
    from app.modules.loans.sync import run_bank_sync

    anb = owner_db.execute(text("select id, tenant_id from organizations where code = :c"), {"c": "ANB"}).one()
    before = len(owner_db.execute(select(RepaymentTransaction.id)).all())
    batch = run_bank_sync(owner_db, anb.tenant_id, anb.id, actor_label="test")
    assert batch.status == "APPLIED"
    assert batch.summary["transactions_new"] == 0 and batch.summary["transactions_duplicate"] > 0
    assert len(owner_db.execute(select(RepaymentTransaction.id)).all()) == before


def test_sync_failure_produces_unknown_not_overdue(owner_db):
    """AC-05 / FR-REP-06: a failed sync never creates a delinquency finding; stale data shows UNKNOWN."""
    from datetime import UTC, datetime, timedelta

    from app.models.loans import Integration
    from app.modules.loans.sync import run_bank_sync

    mfb = owner_db.execute(text("select id, tenant_id from organizations where code = :c"), {"c": "MFB"}).one()
    owner_db.execute(text("update loan_accounts set last_synced_at = :t where bank_org_id = :b"),
                     {"t": datetime.now(UTC) - timedelta(hours=72), "b": mfb.id})
    integ = owner_db.execute(select(Integration).where(Integration.org_id == mfb.id)).scalar()
    integ.simulate_failure = True
    batch = run_bank_sync(owner_db, mfb.tenant_id, mfb.id, actor_label="test")
    assert batch.status == "FAILED"
    loans = owner_db.execute(select(LoanAccount).where(LoanAccount.bank_org_id == mfb.id,
                                                       LoanAccount.link_status == "LINKED")).scalars().all()
    assert loans and all(lo.sync_state == "STALE" and lo.repayment_status == "UNKNOWN" and lo.dpd is None
                         for lo in loans)
    owner_db.rollback()


def test_production_refuses_insecure_defaults():
    """Outside demo/dev/test the API refuses to start with default secrets, insecure cookies or MOCK providers."""
    import pytest as _pytest

    from app.core.config import Settings

    with _pytest.raises(ValueError, match="DAPRO_JWT_SECRET"):
        Settings(env="production", jwt_secret="too-short")
    strong = "x" * 48
    ok = Settings(env="production", jwt_secret=strong, app_db_password="s3cret-app",
                  database_url="postgresql+psycopg://dapro_app:s3cret-app@db:5432/dapro",
                  database_owner_url="postgresql+psycopg://dapro_owner:s3cret-own@db:5432/dapro",
                  cookie_secure=True, email_mode="disabled", sms_mode="disabled", bank_adapter="none")
    assert ok.env == "production" and not ok.is_demo
    with _pytest.raises(ValueError, match="MOCK providers"):
        Settings(env="production", jwt_secret=strong, app_db_password="s3cret-app",
                 database_url="postgresql+psycopg://dapro_app:s3cret-app@db:5432/dapro",
                 database_owner_url="postgresql+psycopg://dapro_owner:s3cret-own@db:5432/dapro", cookie_secure=True)
    assert Settings(env="demo").is_demo  # demo keeps working with defaults
