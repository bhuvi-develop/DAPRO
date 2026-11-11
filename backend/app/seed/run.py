"""Demo dataset entrypoint.  python -m app.seed.run [--if-empty | --reset]

Runs as the schema owner. DEMO data is labelled data_origin=DEMO and the tenant environment_label=DEMO.
Refuses to run when DAPRO_ENV=production. Reset never deletes audit_events (append-only).
"""
import argparse
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, text, update

from app.core import audit
from app.core.config import get_settings
from app.core.db import OwnerSessionLocal
from app.models import Base
from app.models.iam import Tenant, User, UserRole
from app.models.loans import Integration, LoanAccount, LoanSnapshot
from app.models.students import Student
from app.modules.loans.sync import run_bank_sync
from app.modules.students.completion import recompute
from app.seed import data as seed_data
from app.seed.foundation import seed_demo_foundation, seed_isolation_tenant
from app.seed.loans import seed_loans
from app.seed.students import consents, seed_students

KEEP = {"audit_events", "tenants"}


def wipe_tenant(db, tenant_id) -> None:
    db.execute(text("SET LOCAL session_replication_role = default"))
    user_ids = select(User.id).where(User.tenant_id == tenant_id)
    db.execute(delete(UserRole).where(UserRole.user_id.in_(user_ids)))
    db.execute(update(User).where(User.tenant_id == tenant_id).values(student_id=None))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in KEEP or "tenant_id" not in table.c or table.name == "users":
            continue
        if table.name in ("organizations", "org_units", "roles", "user_sessions", "user_invitations"):
            continue
        db.execute(table.delete().where(table.c.tenant_id == tenant_id))
    for name in ("user_sessions", "user_invitations"):
        t = Base.metadata.tables[name]
        db.execute(t.delete().where(t.c.tenant_id == tenant_id))
    db.execute(Base.metadata.tables["users"].delete().where(Base.metadata.tables["users"].c.tenant_id == tenant_id))
    for name in ("roles", "org_units", "organizations"):
        t = Base.metadata.tables[name]
        if name == "org_units":
            db.execute(t.update().where(t.c.tenant_id == tenant_id).values(parent_id=None))
        db.execute(t.delete().where(t.c.tenant_id == tenant_id))


def seed_all(db, existing_demo=None) -> dict:
    seed_data.RNG.seed(20261106)
    F = seed_demo_foundation(db, existing_demo)
    tid = F["tenant"].id
    rows = seed_students(db, F)
    L = seed_loans(db, F, rows)
    seen = set()
    for n, (lo, _) in enumerate(L["loans"]):
        if lo.student_id in seen:
            continue
        seen.add(lo.student_id)
        consents(db, db.get(Student, lo.student_id), withdrawn=n in (9, 27, 44, 61))
    db.flush()
    anb, mfb = F["orgs"]["ANB"], F["orgs"]["MFB"]
    ravi, harish = F["users"]["ravi"], F["users"]["mfb_ops"]
    run_bank_sync(db, tid, mfb.id, actor_id=harish.id, actor_label=harish.full_name, actor_role="BANK_LOAN_OPS")
    # US-06: MFB last succeeded 30 hours ago and the latest scheduled pull failed (data still within freshness window).
    past = datetime.now(UTC) - timedelta(hours=30)
    mfb_loans = select(LoanAccount.id).where(LoanAccount.bank_org_id == mfb.id)
    db.execute(update(LoanAccount).where(LoanAccount.bank_org_id == mfb.id, LoanAccount.last_synced_at.isnot(None))
               .values(last_synced_at=past))
    db.execute(update(LoanSnapshot).where(LoanSnapshot.loan_id.in_(mfb_loans)).values(as_of=past))
    integ = db.execute(select(Integration).where(Integration.org_id == mfb.id)).scalar()
    integ.last_success_at, integ.simulate_failure = past, True
    run_bank_sync(db, tid, mfb.id, actor_label="Scheduler (Celery beat)", actor_role="SYSTEM")
    integ.simulate_failure = False
    run_bank_sync(db, tid, anb.id, actor_id=ravi.id, actor_label=ravi.full_name, actor_role="BANK_LOAN_OPS")
    for row in rows:
        recompute(db, row["student"])
    for row in sorted(rows, key=lambda r: r["student"].created_at)[-40:]:
        s = row["student"]
        audit.write(db, tenant_id=tid, action="student.registered", actor_id=s.created_by, actor_label="College import",
                    actor_role="COLLEGE_ADMIN", org_id=s.college_org_id, target_type="student", target_id=s.id,
                    target_label=s.dapro_ref, payload={"source": s.source}, occurred_at=s.created_at)
    try:
        from app.seed.operations import seed_operations
    except ImportError:
        seed_operations = None
    if seed_operations:
        seed_operations(db, F)
    if existing_demo is None:
        seed_isolation_tenant(db)
    return F


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--if-empty", action="store_true")
    p.add_argument("--reset", action="store_true")
    a = p.parse_args()
    if get_settings().env == "production":
        print("Refusing to seed DEMO data in production", file=sys.stderr)
        return 2
    db = OwnerSessionLocal()
    try:
        demo = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalar()
        if demo and a.if_empty:
            print("[seed] DEMO tenant present; skipping")
            return 0
        if demo and not a.reset:
            print("[seed] DEMO tenant exists; use --reset", file=sys.stderr)
            return 1
        if demo:
            wipe_tenant(db, demo.id)
            db.flush()
        seed_all(db, demo)
        db.commit()
        print("[seed] DEMO dataset ready")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
