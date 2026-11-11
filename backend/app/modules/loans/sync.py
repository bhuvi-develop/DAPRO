"""Bank synchronization: apply a bank feed into the DAPRO read-only mirror (FR-LON-04/05, FR-REP-01/02,
INT-COM-01/03/04, INT-BNK-03, AC-04, AC-05). Runs STARTED -> VALIDATED -> APPLIED or FAILED.
"""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.common.clock import business_today
from app.common.notify import notify
from app.common.policy import get_policy
from app.core import audit
from app.core.config import get_settings
from app.core.ids import uuid7
from app.models.iam import OrgUnit, Role, User, UserRole
from app.models.loans import (
    ImportBatch,
    Integration,
    LoanAccount,
    LoanSnapshot,
    MockBankRecord,
    ReconciliationItem,
    RepaymentSchedule,
    RepaymentTransaction,
    ScheduleInstalment,
)
from app.modules.loans.bank_feed import SOURCE, MockBankAdapter
from app.modules.repayments.engine import evaluate_loan


def _recon(db, tenant_id, key, **kw) -> bool:
    if db.execute(select(ReconciliationItem.id).where(ReconciliationItem.dedupe_key == key,
                                                      ReconciliationItem.status == "OPEN")).scalar():
        return False
    db.add(ReconciliationItem(tenant_id=tenant_id, dedupe_key=key, **kw))
    return True


def bank_integration(db, bank_org_id) -> Integration | None:
    return db.execute(select(Integration).where(Integration.org_id == bank_org_id,
                                                Integration.kind == "BANK_LOAN_FEED")).scalar()


def _bank_admins(db, bank_org_id):
    return db.execute(select(User.id).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id)
                      .where(User.org_id == bank_org_id, Role.code.in_(["BANK_ADMIN", "BANK_LOAN_OPS"]))).scalars().all()


def apply_feed(db, loan: LoanAccount, rec: MockBankRecord, batch: ImportBatch, as_of: date, stats: dict) -> None:
    feed = MockBankAdapter(db, loan.bank_org_id).fetch(rec, as_of)
    m = feed.master
    branch = db.execute(select(OrgUnit.id).where(OrgUnit.org_id == loan.bank_org_id,
                                                 OrgUnit.code == m.pop("branch_code"))).scalar()
    for k, v in m.items():
        setattr(loan, k, v)
    loan.branch_unit_id = branch or loan.branch_unit_id
    loan.source_system, loan.source_record_id = SOURCE, rec.bank_loan_ref

    if feed.instalments:
        cur = db.execute(select(RepaymentSchedule).where(RepaymentSchedule.loan_id == loan.id,
                                                         RepaymentSchedule.is_current.is_(True))).scalar()
        sig = [(i.no, i.due, i.amount) for i in feed.instalments]
        if cur is not None:
            old = db.execute(select(ScheduleInstalment.instalment_no, ScheduleInstalment.due_date,
                                    ScheduleInstalment.amount_due).where(ScheduleInstalment.schedule_id == cur.id)
                             .order_by(ScheduleInstalment.instalment_no)).all()
            if [tuple(o) for o in old] != sig:
                cur.is_current = False
                cur = None
                stats["schedules_changed"] += 1
        if cur is None:
            version = (db.execute(select(RepaymentSchedule.version).where(RepaymentSchedule.loan_id == loan.id)
                                  .order_by(RepaymentSchedule.version.desc()).limit(1)).scalar() or 0) + 1
            cur = RepaymentSchedule(id=uuid7(), tenant_id=loan.tenant_id, loan_id=loan.id, version=version,
                                    schedule_ref=f"{rec.bank_loan_ref}-S{version}",
                                    reason="ORIGINAL" if version == 1 else "RESCHEDULE",
                                    effective_from=feed.instalments[0].due, source_system=SOURCE,
                                    source_batch_id=batch.id)
            db.add(cur)
            db.flush()
            for i in feed.instalments:
                db.add(ScheduleInstalment(tenant_id=loan.tenant_id, schedule_id=cur.id, loan_id=loan.id,
                                          instalment_no=i.no, due_date=i.due, amount_due=i.amount,
                                          principal_component=i.principal, interest_component=i.interest))
            db.flush()
        rows = {r.instalment_no: r for r in db.execute(
            select(ScheduleInstalment).where(ScheduleInstalment.schedule_id == cur.id)).scalars()}
        for i in feed.instalments:
            r = rows[i.no]
            r.bank_allocated_amount, r.bank_status = i.allocated, i.bank_status

    for t in feed.transactions:
        res = db.execute(insert(RepaymentTransaction).values(
            id=uuid7(), tenant_id=loan.tenant_id, loan_id=loan.id, bank_txn_ref=t.ref, posted_on=t.posted,
            value_on=t.value, amount=t.amount, kind=t.kind, channel=t.channel, payment_reference=t.payment_reference,
            reverses_txn_ref=t.reverses, allocations=t.allocations, source_system=SOURCE, source_batch_id=batch.id,
        ).on_conflict_do_nothing(index_elements=["tenant_id", "bank_txn_ref"]).returning(RepaymentTransaction.id))
        if res.first() is not None:
            stats["transactions_new"] += 1
            if t.kind == "PAYMENT" and not t.allocations:
                stats["recon_items"] += _recon(
                    db, loan.tenant_id, f"UNKNOWN_TXN:{t.ref}", bank_org_id=loan.bank_org_id, loan_id=loan.id,
                    student_id=loan.student_id, batch_id=batch.id, kind="UNKNOWN_TRANSACTION", severity="HIGH",
                    summary=f"Bank credit {t.ref} of INR {t.amount} has no instalment allocation",
                    details={"bank_txn_ref": t.ref, "amount": str(t.amount), "posted_on": t.posted.isoformat(),
                             "note": "DAPRO does not allocate payments. Ask the bank to confirm allocation."})
            if t.kind == "REVERSAL":
                stats["recon_items"] += _recon(
                    db, loan.tenant_id, f"REVERSAL:{t.ref}", bank_org_id=loan.bank_org_id, loan_id=loan.id,
                    student_id=loan.student_id, batch_id=batch.id, kind="REVERSAL_REVIEW", severity="MEDIUM",
                    summary=f"Bank reversed payment {t.reverses} ({t.payment_reference})",
                    details={"reversal_ref": t.ref, "reverses": t.reverses, "amount": str(t.amount)})
        else:
            stats["transactions_duplicate"] += 1

    s = feed.snapshot
    db.add(LoanSnapshot(tenant_id=loan.tenant_id, loan_id=loan.id, as_of=datetime.now(UTC), source_system=SOURCE,
                        source_batch_id=batch.id, **s))
    stats["snapshots"] += 1
    loan.sync_state, loan.last_synced_at, loan.last_sync_batch_id = "CURRENT", datetime.now(UTC), batch.id
    db.flush()
    evaluate_loan(db, loan, as_of)


def mark_stale(db, bank_org_id=None) -> int:
    """Loans whose last successful sync is older than policy become STALE (UC-10)."""
    hours = int(get_policy(db, "DATA_FRESHNESS")["value"].get("stale_after_hours", 48))
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    stmt = select(LoanAccount).where(LoanAccount.link_status == "LINKED", LoanAccount.sync_state == "CURRENT",
                                     LoanAccount.last_synced_at < cutoff)
    if bank_org_id:
        stmt = stmt.where(LoanAccount.bank_org_id == bank_org_id)
    n = 0
    for loan in db.execute(stmt).scalars():
        loan.sync_state = "STALE"
        evaluate_loan(db, loan)
        n += 1
    return n


def run_bank_sync(db, tenant_id, bank_org_id, *, actor_id=None, actor_label="system", actor_role=None,
                  correlation_id=None, as_of: date | None = None, loan_ids: list | None = None,
                  data_origin: str = "DEMO") -> ImportBatch:
    as_of = as_of or business_today()
    now = datetime.now(UTC)
    corr = correlation_id or str(uuid7())
    integ = bank_integration(db, bank_org_id)
    batch = ImportBatch(id=uuid7(), tenant_id=tenant_id, org_id=bank_org_id, kind="BANK_SYNC", source=SOURCE,
                        status="RUNNING", uploaded_by=actor_id, correlation_id=corr, started_at=now,
                        data_origin=data_origin, file_name=f"mock-feed-{as_of.isoformat()}")
    db.add(batch)
    db.flush()
    stats = {"loans_processed": 0, "transactions_new": 0, "transactions_duplicate": 0, "snapshots": 0,
             "schedules_changed": 0, "recon_items": 0, "stale_marked": 0}

    mode = integ.mode if integ else "NOT_CONFIGURED"
    failure = None
    if get_settings().bank_adapter != "mock" or mode in ("NOT_CONFIGURED", "DISABLED"):
        failure = f"Bank feed is {mode}; no data can be synchronized."
    elif integ.simulate_failure:
        failure = "Simulated failure: the bank feed file did not arrive (demo control)."

    if failure:
        batch.status, batch.finished_at = "FAILED", datetime.now(UTC)
        batch.errors = [{"row": None, "message": failure}]
        if integ:
            integ.health, integ.last_failure_at, integ.last_error = "FAILED", now, failure
            integ.consecutive_failures += 1
        stats["stale_marked"] = mark_stale(db, bank_org_id)
        stats["recon_items"] += _recon(db, tenant_id, f"SYNC_FAILURE:{bank_org_id}:{as_of}", bank_org_id=bank_org_id,
                                       batch_id=batch.id, kind="SYNC_FAILURE", severity="HIGH",
                                       summary=failure, details={"as_of": as_of.isoformat(), "correlation_id": corr})
        if integ and integ.consecutive_failures >= 3:
            for uid in _bank_admins(db, bank_org_id):
                notify(db, tenant_id, uid, "INTEGRATION_INCIDENT", "Bank feed failed 3 times in a row",
                       "Repayment data is now stale. No delinquency findings are created from failed syncs.",
                       "/admin/integrations", "CRITICAL")
        batch.summary = stats
        audit.write(db, tenant_id=tenant_id, action="bank.sync", outcome="FAILURE", actor_id=actor_id,
                    actor_label=actor_label, actor_role=actor_role, org_id=bank_org_id, target_type="import_batch",
                    target_id=batch.id, correlation_id=corr, payload={"error": failure, **stats})
        return batch

    batch.status = "VALIDATED"
    adapter = MockBankAdapter(db, bank_org_id)
    stmt = select(LoanAccount).where(LoanAccount.bank_org_id == bank_org_id, LoanAccount.link_status == "LINKED")
    if loan_ids:
        stmt = stmt.where(LoanAccount.id.in_(loan_ids))
    known = set()
    for loan in db.execute(stmt).scalars().all():
        known.add(loan.bank_loan_ref)
        rec = adapter.lookup(loan.bank_loan_ref)
        if rec is None:
            stats["recon_items"] += _recon(db, tenant_id, f"MISSING_AT_BANK:{loan.id}", bank_org_id=bank_org_id,
                                           loan_id=loan.id, student_id=loan.student_id, batch_id=batch.id,
                                           kind="MISSING_AT_BANK", severity="HIGH",
                                           summary=f"{loan.bank_loan_ref} is linked in DAPRO but absent from bank feed")
            continue
        apply_feed(db, loan, rec, batch, as_of, stats)
        stats["loans_processed"] += 1
    if not loan_ids:
        linked_or_pending = set(db.execute(select(LoanAccount.bank_loan_ref)
                                           .where(LoanAccount.bank_org_id == bank_org_id)).scalars())
        for ref in adapter.all_refs():
            if ref not in linked_or_pending:
                stats["recon_items"] += _recon(
                    db, tenant_id, f"UNMATCHED_LOAN:{bank_org_id}:{ref}", bank_org_id=bank_org_id, batch_id=batch.id,
                    kind="UNMATCHED_LOAN", severity="MEDIUM",
                    summary=f"Bank loan {ref} has no linked DAPRO student",
                    details={"bank_loan_ref": ref, "note": "Link through Student 360 after identity validation."})
    batch.total_rows = batch.valid_rows = stats["loans_processed"]
    batch.applied_rows = stats["transactions_new"]
    batch.duplicate_rows = stats["transactions_duplicate"]
    batch.status, batch.finished_at, batch.summary = "APPLIED", datetime.now(UTC), stats
    if integ:
        integ.health, integ.last_success_at, integ.consecutive_failures, integ.last_error = "HEALTHY", now, 0, None
    audit.write(db, tenant_id=tenant_id, action="bank.sync", outcome="SUCCESS", actor_id=actor_id,
                actor_label=actor_label, actor_role=actor_role, org_id=bank_org_id, target_type="import_batch",
                target_id=batch.id, correlation_id=corr, payload=stats)
    return batch
