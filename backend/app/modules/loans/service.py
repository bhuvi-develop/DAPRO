"""Loan linkage, bank mirror views, sync trigger and reconciliation (FR-LON-01..08, FR-REP-08)."""
from datetime import UTC, datetime

from sqlalchemy import select, true

from app.common.pagination import paginate
from app.core import masking
from app.core.errors import BusinessError, Forbidden, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.models.iam import Organization
from app.models.loans import (
    Guarantor,
    ImportBatch,
    LoanAccount,
    LoanParty,
    LoanSnapshot,
    ReconciliationItem,
    RepaymentSchedule,
    RepaymentTransaction,
    ScheduleInstalment,
    Witness,
)
from app.models.students import Student
from app.modules.loans import repo
from app.modules.loans.bank_feed import MockBankAdapter
from app.modules.loans.sync import run_bank_sync


def norm(s: str | None) -> str:
    return " ".join(sorted((s or "").upper().replace(".", " ").split()))


def iso(v):
    return v.isoformat() if v else None


def freshness(loan) -> dict:
    return {"source": loan.source_system, "as_of": iso(loan.last_synced_at), "sync_state": loan.sync_state}


def loan_row(ctx, loan, student_name=None, dapro_ref=None, bank_name=None, branch_name=None) -> dict:
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    return {
        "id": str(loan.id), "bank_loan_ref": loan.bank_loan_ref, "bank_org_id": str(loan.bank_org_id),
        "bank_name": bank_name, "branch_name": branch_name, "student_id": str(loan.student_id) if loan.student_id else None,
        "student_name": student_name, "dapro_ref": dapro_ref, "product_name": loan.product_name,
        "bank_status": loan.bank_status, "link_status": loan.link_status, "repayment_status": loan.repayment_status,
        "dpd": loan.dpd if masking.financial_visible(ctx) else None,
        "dpd_bucket": loan.dpd_bucket if masking.financial_visible(ctx) else None,
        "sanctioned_amount": m(loan.sanctioned_amount), "disbursed_amount": m(loan.disbursed_amount),
        "overdue_amount": m(loan.overdue_amount), "principal_outstanding": m(loan.principal_outstanding),
        "emi_amount": m(loan.emi_amount), "next_due_date": iso(loan.next_due_date),
        "next_due_amount": m(loan.next_due_amount), "currency": loan.currency, "sync_state": loan.sync_state,
        "last_synced_at": iso(loan.last_synced_at), "moratorium_end": iso(loan.moratorium_end),
        "repayment_start": iso(loan.repayment_start), "data_origin": loan.data_origin,
        "financial_restricted": not masking.financial_visible(ctx), "freshness": freshness(loan),
    }


SORTABLE = {"dpd": LoanAccount.dpd, "bank_loan_ref": LoanAccount.bank_loan_ref, "next_due_date": LoanAccount.next_due_date,
            "overdue_amount": LoanAccount.overdue_amount, "last_synced_at": LoanAccount.last_synced_at,
            "created_at": LoanAccount.created_at, "student_name": Student.full_name}


def order_by(sort: str | None, default):
    if sort and sort.lstrip("-") in SORTABLE:
        col = SORTABLE[sort.lstrip("-")]
        return (col.desc().nullslast() if sort.startswith("-") else col.asc().nullslast(), LoanAccount.id)
    return default


def list_loans(ctx, f: dict, page: int, size: int, sort: str | None = None) -> dict:
    stmt = repo.loan_list_stmt(ctx, f).order_by(*order_by(sort, (LoanAccount.dpd.desc().nullslast(),
                                                                 LoanAccount.bank_loan_ref)))
    rows, total, page, size = paginate(ctx.db, stmt, page, size, scalars=False)
    return {"items": [loan_row(ctx, *r) for r in rows], "total": total, "page": page, "size": size}


def _get(ctx, loan_id) -> LoanAccount:
    loan = repo.get_scoped(ctx, loan_id)
    if loan is None:
        raise NotFound("Loan account")
    return loan


def loan_detail(ctx, loan_id) -> dict:
    db = ctx.db
    loan = _get(ctx, loan_id)
    s = db.get(Student, loan.student_id) if loan.student_id else None
    bank = db.get(Organization, loan.bank_org_id)
    from app.models.iam import OrgUnit
    br = db.get(OrgUnit, loan.branch_unit_id) if loan.branch_unit_id else None
    out = loan_row(ctx, loan, s.full_name if s else None, s.dapro_ref if s else None, bank.name, br.name if br else None)
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    out.update({"bank_borrower_ref": loan.bank_borrower_ref, "scheme": loan.scheme,
                "sanction_date": iso(loan.sanction_date), "first_disbursement_date": iso(loan.first_disbursement_date),
                "tenure_months": loan.tenure_months,
                "interest_rate_pct": str(loan.interest_rate_pct) if loan.interest_rate_pct and masking.financial_visible(ctx) else None,
                "link_validation": loan.link_validation, "linked_at": iso(loan.linked_at),
                "source_system": loan.source_system, "source_record_id": loan.source_record_id,
                "status_evaluated_at": iso(loan.status_evaluated_at)})
    snap = repo.latest_snapshot(db, loan.id)
    out["snapshot"] = None if snap is None else {
        "as_of": iso(snap.as_of), "principal_outstanding": m(snap.principal_outstanding),
        "interest_charges": m(snap.interest_charges), "overdue_amount": m(snap.overdue_amount),
        "total_due": m(snap.total_due), "bank_dpd": snap.bank_dpd if masking.financial_visible(ctx) else None,
        "bank_status": snap.bank_status, "freshness": {"source": snap.source_system, "as_of": iso(snap.as_of),
                                                       "sync_state": loan.sync_state}}
    out["parties"] = [{"id": str(p.id), "role": p.party_role, "full_name": p.full_name, "relationship": p.relationship,
                       "source": p.source} for p in db.execute(select(LoanParty).where(LoanParty.loan_id == loan.id))
                      .scalars()]
    out["guarantors"] = None
    if ctx.can("guarantor:read"):
        out["guarantors"] = [{"id": str(g.id), "full_name": g.full_name, "relationship": g.relationship_to_borrower,
                              "agreement_ref": g.agreement_ref, "guarantee_status": g.guarantee_status,
                              "verification": g.verification, "communication_permitted": g.communication_permitted}
                             for g in db.execute(select(Guarantor).where(Guarantor.loan_id == loan.id)).scalars()]
    out["witnesses"] = None
    if ctx.can("witness:read"):
        out["witnesses"] = [{"id": str(w.id), "full_name": w.full_name, "document_ref": w.document_ref,
                             "witnessed_on": iso(w.witnessed_on), "verification": w.verification}
                            for w in db.execute(select(Witness).where(Witness.loan_id == loan.id)).scalars()]
    out["sync_history"] = [batch_row(b) for b in repo.batches_for(db, loan) if b]
    return out


def batch_row(b: ImportBatch) -> dict:
    return {"id": str(b.id), "kind": b.kind, "source": b.source, "status": b.status, "file_name": b.file_name,
            "summary": b.summary, "errors": b.errors, "total_rows": b.total_rows, "applied_rows": b.applied_rows,
            "duplicate_rows": b.duplicate_rows, "error_rows": b.error_rows, "org_id": str(b.org_id),
            "correlation_id": b.correlation_id, "data_origin": b.data_origin, "started_at": iso(b.started_at),
            "finished_at": iso(b.finished_at), "created_at": iso(b.created_at)}


def schedule(ctx, loan_id) -> dict:
    loan = _get(ctx, loan_id)
    db = ctx.db
    versions = db.execute(select(RepaymentSchedule).where(RepaymentSchedule.loan_id == loan.id)
                          .order_by(RepaymentSchedule.version.desc())).scalars().all()
    cur = next((v for v in versions if v.is_current), None)
    insts = [] if cur is None else db.execute(select(ScheduleInstalment).where(ScheduleInstalment.schedule_id == cur.id)
                                              .order_by(ScheduleInstalment.instalment_no)).scalars().all()
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    return {"loan_id": str(loan.id), "freshness": freshness(loan),
            "versions": [{"id": str(v.id), "version": v.version, "schedule_ref": v.schedule_ref, "reason": v.reason,
                          "effective_from": iso(v.effective_from), "is_current": v.is_current,
                          "received_at": iso(v.received_at), "source": v.source_system} for v in versions],
            "instalments": [{"no": i.instalment_no, "due_date": iso(i.due_date), "amount_due": m(i.amount_due),
                             "principal": m(i.principal_component), "interest": m(i.interest_component),
                             "bank_allocated": m(i.bank_allocated_amount), "bank_status": i.bank_status,
                             "status": i.status if loan.sync_state == "CURRENT" else "UNKNOWN", "dpd": i.dpd}
                            for i in insts]}


def transactions(ctx, loan_id) -> dict:
    loan = _get(ctx, loan_id)
    rows = ctx.db.execute(select(RepaymentTransaction).where(RepaymentTransaction.loan_id == loan.id)
                          .order_by(RepaymentTransaction.posted_on.desc(), RepaymentTransaction.bank_txn_ref)).scalars().all()
    reversed_refs = {t.reverses_txn_ref: t.bank_txn_ref for t in rows if t.reverses_txn_ref}
    return {"loan_id": str(loan.id), "freshness": freshness(loan), "items": [
        {"id": str(t.id), "bank_txn_ref": t.bank_txn_ref, "posted_on": iso(t.posted_on), "value_on": iso(t.value_on),
         "amount": masking.money(ctx, t.amount), "kind": t.kind, "channel": t.channel,
         "payment_reference": t.payment_reference, "reverses_txn_ref": t.reverses_txn_ref,
         "reversed_by": reversed_refs.get(t.bank_txn_ref), "allocations": t.allocations if masking.financial_visible(ctx) else [],
         "allocated": bool(t.allocations), "source": t.source_system, "received_at": iso(t.received_at)} for t in rows]}


def snapshots(ctx, loan_id) -> dict:
    loan = _get(ctx, loan_id)
    rows = ctx.db.execute(select(LoanSnapshot).where(LoanSnapshot.loan_id == loan.id)
                          .order_by(LoanSnapshot.as_of.desc()).limit(60)).scalars().all()
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    return {"loan_id": str(loan.id), "items": [
        {"id": str(s.id), "as_of": iso(s.as_of), "principal_outstanding": m(s.principal_outstanding),
         "interest_charges": m(s.interest_charges), "overdue_amount": m(s.overdue_amount), "total_due": m(s.total_due),
         "bank_dpd": s.bank_dpd, "bank_status": s.bank_status, "source": s.source_system,
         "batch_id": str(s.source_batch_id) if s.source_batch_id else None} for s in rows]}


def _sync_one(ctx, loan):
    return run_bank_sync(ctx.db, ctx.tenant_id, loan.bank_org_id, actor_id=ctx.user_id, actor_label=ctx.user_name,
                         actor_role=ctx.role, correlation_id=ctx.correlation_id, loan_ids=[loan.id],
                         data_origin=loan.data_origin)


def link(ctx, student_id, bank_org_id, bank_loan_ref: str, recon_item=None) -> dict:
    db = ctx.db
    ref = bank_loan_ref.strip()
    if ctx.org_type != "PLATFORM" and bank_org_id != ctx.org_id:
        raise Forbidden("You can only link loans of your own bank.")
    s = db.get(Student, student_id)
    if s is None:
        raise NotFound("Student")
    rec = MockBankAdapter(db, bank_org_id).lookup(ref)
    if rec is None:
        ctx.audit("loan.link", target_type="student", target_id=s.id, target_label=s.dapro_ref, outcome="FAILURE",
                  payload={"bank_loan_ref": ref, "reason": "BANK_REFERENCE_NOT_FOUND"})
        ctx.commit()
        raise BusinessError("BANK_REFERENCE_NOT_FOUND", f"The bank does not recognise loan reference {ref}.",
                            "Check the reference with the bank loan system and retry.", 422)
    loan = db.execute(select(LoanAccount).where(LoanAccount.bank_org_id == bank_org_id,
                                                LoanAccount.bank_loan_ref == ref)).scalar()
    if loan is not None and loan.link_status == "LINKED":
        if loan.student_id != s.id:
            raise BusinessError("DUPLICATE_REFERENCE", f"{ref} is already linked to another student.",
                                "Open the reconciliation queue if you believe the existing link is wrong.", 409)
        raise BusinessError("ALREADY_LINKED", f"{ref} is already linked to this student.", None, 409)
    name_ok, dob_ok = norm(rec.borrower_name) == norm(s.full_name), rec.borrower_dob == s.dob
    validation = {"method": "BANK_REFERENCE_LOOKUP", "source": "MOCK_BANK_FEED", "name_match": name_ok,
                  "dob_match": dob_ok, "validated_at": datetime.now(UTC).isoformat()}
    if not (name_ok and dob_ok):
        validation.update(bank_name=rec.borrower_name, dapro_name=s.full_name)
    if loan is None:
        loan = LoanAccount(id=uuid7(), tenant_id=ctx.tenant_id, bank_org_id=bank_org_id, bank_loan_ref=ref,
                           data_origin=s.data_origin)
        db.add(loan)
    loan.student_id, loan.college_org_id, loan.link_validation = s.id, s.college_org_id, validation
    if name_ok and dob_ok:
        loan.link_status, loan.linked_by, loan.linked_at = "LINKED", ctx.user_id, datetime.now(UTC)
        db.flush()
        ctx.audit("loan.linked", target_type="loan", target_id=loan.id, target_label=ref,
                  payload={"student": s.dapro_ref, "validation": "EXACT_NAME_DOB"})
        batch = _sync_one(ctx, loan)
        if recon_item is not None:
            recon_item.loan_id = loan.id
        ctx.commit()
        return {"loan_id": str(loan.id), "link_status": "LINKED", "sync_batch_id": str(batch.id),
                "sync_status": batch.status, "validation": validation}
    loan.link_status = "PENDING_REVIEW"
    db.flush()
    db.add(ReconciliationItem(tenant_id=ctx.tenant_id, bank_org_id=bank_org_id, loan_id=loan.id, student_id=s.id,
                              kind="AMBIGUOUS_LINK", severity="HIGH", dedupe_key=f"AMBIGUOUS_LINK:{loan.id}",
                              summary=f"Identity mismatch linking {ref} to {s.dapro_ref}", details=validation))
    ctx.audit("loan.link_pending_review", target_type="loan", target_id=loan.id, target_label=ref,
              payload={"student": s.dapro_ref, "name_match": name_ok, "dob_match": dob_ok})
    ctx.commit()
    return {"loan_id": str(loan.id), "link_status": "PENDING_REVIEW", "validation": validation,
            "message": "Identity did not match exactly. Sent to reconciliation for human review."}


def _org_filter(ctx, col):
    return true() if ctx.org_type == "PLATFORM" else col == ctx.org_id


def list_imports(ctx, page, size, status=None, kind=None) -> dict:
    stmt = select(ImportBatch).where(_org_filter(ctx, ImportBatch.org_id)).order_by(ImportBatch.created_at.desc())
    if status:
        stmt = stmt.where(ImportBatch.status == status)
    if kind:
        stmt = stmt.where(ImportBatch.kind == kind)
    rows, total, page, size = paginate(ctx.db, stmt, page, size)
    return {"items": [batch_row(b) for b in rows], "total": total, "page": page, "size": size}


def get_import(ctx, batch_id) -> dict:
    b = ctx.db.execute(select(ImportBatch).where(ImportBatch.id == batch_id,
                                                 _org_filter(ctx, ImportBatch.org_id))).scalar()
    if b is None:
        raise NotFound("Import batch")
    out = batch_row(b)
    out["reconciliation_items"] = [recon_row(r) for r in ctx.db.execute(
        select(ReconciliationItem).where(ReconciliationItem.batch_id == b.id)).scalars()]
    return out


def recon_row(r: ReconciliationItem, extra: dict | None = None) -> dict:
    return {"id": str(r.id), "kind": r.kind, "severity": r.severity, "summary": r.summary, "details": r.details,
            "status": r.status, "resolution": r.resolution, "loan_id": str(r.loan_id) if r.loan_id else None,
            "student_id": str(r.student_id) if r.student_id else None,
            "bank_org_id": str(r.bank_org_id) if r.bank_org_id else None,
            "batch_id": str(r.batch_id) if r.batch_id else None, "resolved_at": iso(r.resolved_at),
            "created_at": iso(r.created_at), **(extra or {})}


def list_recon(ctx, page, size, kind=None, status="OPEN", severity=None) -> dict:
    stmt = (select(ReconciliationItem, LoanAccount.bank_loan_ref, Student.full_name, Student.dapro_ref)
            .outerjoin(LoanAccount, LoanAccount.id == ReconciliationItem.loan_id)
            .outerjoin(Student, Student.id == ReconciliationItem.student_id)
            .where(_org_filter(ctx, ReconciliationItem.bank_org_id)).order_by(ReconciliationItem.created_at.desc()))
    for val, col in ((kind, ReconciliationItem.kind), (status, ReconciliationItem.status),
                     (severity, ReconciliationItem.severity)):
        if val:
            stmt = stmt.where(col == val)
    rows, total, page, size = paginate(ctx.db, stmt, page, size, scalars=False)
    return {"items": [recon_row(r, {"bank_loan_ref": ref, "student_name": n, "dapro_ref": d}) for r, ref, n, d in rows],
            "total": total, "page": page, "size": size}


ALLOWED = {"AMBIGUOUS_LINK": {"CONFIRM_LINK", "REJECT_LINK"}, "UNMATCHED_LOAN": {"LINK_TO_STUDENT", "DISMISS"}}


def resolve(ctx, item_id, action: str, resolution: str, student_id=None) -> dict:
    db = ctx.db
    item = db.execute(select(ReconciliationItem).where(ReconciliationItem.id == item_id,
                                                       _org_filter(ctx, ReconciliationItem.bank_org_id))).scalar()
    if item is None:
        raise NotFound("Reconciliation item")
    if item.status != "OPEN":
        raise BusinessError("ALREADY_RESOLVED", "This item is already closed.", "Refresh the queue.", 409)
    allowed = ALLOWED.get(item.kind, {"RESOLVE", "DISMISS"})
    if action not in allowed:
        raise ValidationFailed(f"Action {action} is not valid for {item.kind}.",
                               [{"field": "action", "message": f"Use one of {sorted(allowed)}"}])
    result: dict = {}
    if action in ("CONFIRM_LINK", "REJECT_LINK"):
        loan = db.get(LoanAccount, item.loan_id)
        if loan is None:
            raise NotFound("Loan account")
        if action == "CONFIRM_LINK":
            loan.link_status, loan.linked_by, loan.linked_at = "LINKED", ctx.user_id, datetime.now(UTC)
            loan.link_validation = {**(loan.link_validation or {}), "human_confirmed_by": str(ctx.user_id),
                                    "human_rationale": resolution}
            db.flush()
            ctx.audit("loan.linked", target_type="loan", target_id=loan.id, target_label=loan.bank_loan_ref,
                      payload={"via": "RECONCILIATION", "rationale": resolution})
            result["sync_batch_id"] = str(_sync_one(ctx, loan).id)
        else:
            loan.link_status = "REJECTED"
            ctx.audit("loan.link_rejected", target_type="loan", target_id=loan.id, target_label=loan.bank_loan_ref,
                      payload={"rationale": resolution})
    elif action == "LINK_TO_STUDENT":
        if not student_id:
            raise ValidationFailed("Choose the student to link.", [{"field": "student_id", "message": "Required"}])
        result = link(ctx, student_id, item.bank_org_id, item.details.get("bank_loan_ref", ""), recon_item=item)
        if result["link_status"] != "LINKED":
            item.status, item.resolution = "RESOLVED", f"Routed to identity review: {resolution}"
    item.status = "DISMISSED" if action in ("DISMISS", "REJECT_LINK") else "RESOLVED"
    item.resolution, item.resolved_by, item.resolved_at = resolution, ctx.user_id, datetime.now(UTC)
    ctx.audit("reconciliation.resolved", target_type="reconciliation_item", target_id=item.id,
              payload={"kind": item.kind, "action": action, "resolution": resolution})
    ctx.commit()
    return {"id": str(item.id), "status": item.status, **result}


def trigger_sync(ctx, bank_org_id) -> dict:
    if bank_org_id != ctx.org_id:
        raise Forbidden("You can only synchronize your own bank feed.")
    from app.workers.tasks_financial import sync_bank

    res = sync_bank.delay(str(ctx.tenant_id), str(bank_org_id), str(ctx.user_id), ctx.user_name, ctx.role,
                          ctx.correlation_id)
    out = {"status": "QUEUED", "task_id": res.id}
    if res.ready():
        out["batch_id"] = res.get()
        b = ctx.db.get(ImportBatch, out["batch_id"])
        if b is not None:
            ctx.db.refresh(b)
            out["status"] = b.status
    return out
