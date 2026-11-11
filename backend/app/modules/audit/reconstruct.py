"""Case reconstruction (RD 11.3): why a case was created, prioritised and disposed, from stored facts only."""
from sqlalchemy import or_, select

from app.core import masking
from app.core.errors import NotFound
from app.core.scope import case_clause
from app.models.engagement import Communication, Grievance
from app.models.iam import User
from app.models.loans import LoanAccount, LoanSnapshot, RepaymentSchedule, RepaymentTransaction
from app.models.ops import (
    Case,
    CaseEvent,
    CaseFollowUp,
    Evidence,
    FieldVisit,
    PaymentCommitment,
    RiskIndicator,
    RiskReview,
)
from app.models.platform import AuditEvent
from app.models.students import EmploymentRecord, Student, StudentAddress
from app.modules.audit.service import event_row, iso


def _snap(ctx, s):
    if s is None:
        return None
    return {"as_of": iso(s.as_of), "overdue_amount": masking.money(ctx, s.overdue_amount), "bank_dpd": s.bank_dpd,
            "principal_outstanding": masking.money(ctx, s.principal_outstanding), "bank_status": s.bank_status,
            "source": s.source_system, "batch_id": str(s.source_batch_id) if s.source_batch_id else None}


def _names(db, ids):
    ids = {i for i in ids if i}
    if not ids:
        return {}
    return {u.id: u.full_name for u in db.execute(select(User).where(User.id.in_(ids))).scalars()}


def completeness(case, loan, snap_at, inds, events, fus, visits) -> dict:
    checks = [("student_reference", True, "Student DAPRO reference recorded")]
    if case.loan_id:
        checks.append(("loan_reference", loan is not None, "Bank loan reference recorded"))
        checks.append(("bank_snapshot_at_creation", snap_at is not None,
                       "Bank-sourced snapshot existing at case creation"))
    if case.source == "RISK_INDICATOR":
        checks.append(("risk_basis", any(i.rule_version for i in inds), "Triggering indicator with rule version"))
    checks.append(("case_history", len(events) > 0, "Case event history"))
    checks.append(("owner_assigned", case.owner_id is not None or case.status == "NEW", "Responsible owner"))
    if case.status not in ("NEW", "ASSIGNED"):
        checks.append(("follow_up_record", bool(fus or visits), "Documented contact attempts or visits"))
    if case.status in ("RESOLVED", "CLOSED"):
        checks.append(("disposition_evidence",
                       bool(case.resolution_type and (case.resolution_evidence or case.resolution_notes)),
                       "Disposition with evidence"))
    for v in visits:
        if v.review_status == "PENDING":
            checks.append((f"visit_review_{v.id}", False, "Field visit awaiting supervisor review"))
    items = [{"key": k, "ok": ok, "label": label} for k, ok, label in checks]
    missing = [i["label"] for i in items if not i["ok"]]
    return {"status": "COMPLETE" if not missing else "INCOMPLETE", "checks": items, "missing": missing}


def _load(db, case):
    st = db.get(Student, case.student_id)
    loan = db.get(LoanAccount, case.loan_id) if case.loan_id else None
    d = {"st": st, "loan": loan, "snap_at": None, "snap_now": None, "sched": None, "txns": []}
    if loan:
        snaps = select(LoanSnapshot).where(LoanSnapshot.loan_id == loan.id).order_by(LoanSnapshot.as_of.desc()).limit(1)
        d["snap_at"] = db.execute(snaps.where(LoanSnapshot.as_of <= case.created_at)).scalar()
        d["snap_now"] = db.execute(snaps).scalar()
        d["sched"] = db.execute(select(RepaymentSchedule).where(RepaymentSchedule.loan_id == loan.id,
                                                                RepaymentSchedule.is_current.is_(True))).scalar()
        d["txns"] = db.execute(select(RepaymentTransaction).where(RepaymentTransaction.loan_id == loan.id)
                               .order_by(RepaymentTransaction.posted_on.desc()).limit(10)).scalars().all()
    d["inds"] = db.execute(select(RiskIndicator).where(or_(RiskIndicator.case_id == case.id,
                                                           RiskIndicator.student_id == case.student_id))
                           .order_by(RiskIndicator.generated_at.desc()).limit(20)).scalars().all()
    ids = [i.id for i in d["inds"]]
    d["reviews"] = db.execute(select(RiskReview).where(RiskReview.indicator_id.in_(ids))
                              .order_by(RiskReview.created_at)).scalars().all() if ids else []
    d["addrs"] = db.execute(select(StudentAddress).where(StudentAddress.student_id == st.id)
                            .order_by(StudentAddress.created_at.desc())).scalars().all()
    d["emps"] = db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == st.id)
                           .order_by(EmploymentRecord.reported_on.desc())).scalars().all()
    d["comms"] = db.execute(select(Communication).where(or_(Communication.case_id == case.id,
                                                            Communication.student_id == st.id))
                            .order_by(Communication.created_at.desc()).limit(30)).scalars().all()
    d["fus"] = db.execute(select(CaseFollowUp).where(CaseFollowUp.case_id == case.id)
                          .order_by(CaseFollowUp.contacted_at)).scalars().all()
    d["visits"] = db.execute(select(FieldVisit).where(FieldVisit.case_id == case.id)
                             .order_by(FieldVisit.created_at)).scalars().all()
    d["events"] = db.execute(select(CaseEvent).where(CaseEvent.case_id == case.id)
                             .order_by(CaseEvent.created_at)).scalars().all()
    d["commits"] = db.execute(select(PaymentCommitment).where(PaymentCommitment.case_id == case.id)).scalars().all()
    d["evid"] = db.execute(select(Evidence).where(Evidence.case_id == case.id)).scalars().all()
    d["grvs"] = db.execute(select(Grievance).where(or_(Grievance.case_id == case.id,
                                                       Grievance.student_id == st.id))).scalars().all()
    targets = [str(case.id), str(st.id)] + ([str(loan.id)] if loan else [])
    d["aud"] = db.execute(select(AuditEvent).where(AuditEvent.target_id.in_(targets))
                          .order_by(AuditEvent.seq)).scalars().all()
    d["names"] = _names(db, [case.owner_id, case.opened_by, case.closed_by] + [r.reviewer_id for r in d["reviews"]]
                        + [v.officer_id for v in d["visits"]] + [v.reviewer_id for v in d["visits"]]
                        + [f.actor_id for f in d["fus"]])
    return d


def reconstruct(ctx, case_id) -> dict:
    case = ctx.db.execute(select(Case).where(Case.id == case_id, case_clause(ctx))).scalar()
    if case is None:
        raise NotFound("Case")
    d = _load(ctx.db, case)
    st, loan, sched = d["st"], d["loan"], d["sched"]
    nm = d["names"].get
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    out = {
        "case": {"id": str(case.id), "case_ref": case.case_ref, "category": case.category, "reason": case.reason,
                 "source": case.source, "source_ref": case.source_ref, "priority": case.priority,
                 "status": case.status, "owner": nm(case.owner_id), "opened_by": nm(case.opened_by),
                 "created_at": iso(case.created_at), "due_on": iso(case.due_on), "next_action": case.next_action},
        "student": {"id": str(st.id), "dapro_ref": st.dapro_ref, "college_student_id": st.college_student_id,
                    "full_name": st.full_name, "lifecycle_status": st.lifecycle_status},
        "loan": None if loan is None else {"id": str(loan.id), "bank_loan_ref": loan.bank_loan_ref,
                                           "link_status": loan.link_status, "link_validation": loan.link_validation,
                                           "sync_state": loan.sync_state, "last_synced_at": iso(loan.last_synced_at)},
        "bank_snapshot_at_creation": _snap(ctx, d["snap_at"]), "bank_snapshot_now": _snap(ctx, d["snap_now"]),
        "schedule": None if sched is None else {"schedule_ref": sched.schedule_ref, "version": sched.version,
                                                "source": sched.source_system, "received_at": iso(sched.received_at)},
        "transactions": [{"bank_txn_ref": t.bank_txn_ref, "posted_on": iso(t.posted_on), "kind": t.kind,
                          "amount": m(t.amount)} for t in d["txns"]],
        "risk_indicators": [{"id": str(i.id), "rule_code": i.rule_code, "rule_version": i.rule_version,
                             "category": i.category, "severity": i.severity, "title": i.title,
                             "explanation": i.explanation, "evidence": i.evidence, "status": i.status,
                             "generated_at": iso(i.generated_at)} for i in d["inds"]],
        "reviews": [{"indicator_id": str(r.indicator_id), "reviewer": nm(r.reviewer_id), "decision": r.decision,
                     "rationale": r.rationale, "override_severity": r.override_severity, "at": iso(r.created_at)}
                    for r in d["reviews"]],
        "addresses": [{"kind": a.kind, "city": a.city, "country": a.country, "source": a.source_type,
                       "verification": a.verification, "method": a.verification_method, "is_current": a.is_current,
                       "effective_from": iso(a.effective_from)} for a in d["addrs"]],
        "employment": [{"status": e.status, "employer": e.employer_name, "source": e.source,
                        "verification": e.verification, "reported_on": iso(e.reported_on),
                        "is_current": e.is_current} for e in d["emps"]],
        "communications": [{"channel": c.channel, "purpose": c.purpose, "template": c.template_code,
                            "template_version": c.template_version, "status": c.status,
                            "block_reason": c.block_reason, "provider_mode": c.provider_mode,
                            "at": iso(c.created_at)} for c in d["comms"]],
        "follow_ups": [{"channel": f.channel, "outcome": f.outcome, "notes": f.notes, "by": nm(f.actor_id),
                        "at": iso(f.contacted_at)} for f in d["fus"]],
        "field_visits": [{"id": str(v.id), "officer": nm(v.officer_id), "status": v.status, "outcome": v.outcome,
                          "visited_at": iso(v.visited_at), "review_status": v.review_status,
                          "reviewer": nm(v.reviewer_id), "review_notes": v.review_notes,
                          "safety_incident": v.safety_incident, "location_captured": v.location_captured}
                         for v in d["visits"]],
        "commitments": [{"amount": m(c.amount), "promised_date": iso(c.promised_date), "source": c.source,
                         "status": c.status, "bank_txn_ref": c.bank_txn_ref} for c in d["commits"]],
        "evidence": [{"title": e.title, "kind": e.kind, "sha256": e.sha256, "quality": e.evidence_quality,
                      "at": iso(e.created_at)} for e in d["evid"]],
        "grievances": [{"ref": g.ref, "category": g.category, "status": g.status, "resolution": g.resolution}
                       for g in d["grvs"]],
        "case_events": [{"type": e.event_type, "from": e.from_status, "to": e.to_status, "summary": e.summary,
                         "at": iso(e.created_at)} for e in d["events"]],
        "disposition": {"status": case.status, "resolution_type": case.resolution_type,
                        "resolution_notes": case.resolution_notes, "resolution_evidence": case.resolution_evidence,
                        "resolved_at": iso(case.resolved_at), "closed_at": iso(case.closed_at),
                        "closed_by": nm(case.closed_by)},
        "audit_events": [event_row(e) for e in d["aud"]],
    }
    out["completeness"] = completeness(case, loan, d["snap_at"], d["inds"], d["events"], d["fus"], d["visits"])
    ctx.audit("audit.case_reconstructed", target_type="case", target_id=case.id, target_label=case.case_ref,
              purpose=ctx.purpose or "AUDIT")
    ctx.commit()
    return out
