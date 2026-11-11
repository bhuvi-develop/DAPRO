"""Explainable rule engine (FR-RSK-01..08, RD 10.3). Prioritises human review only.

Indicators are never rewritten: when a condition clears, the open indicator is marked SUPERSEDED with a note.
Language is neutral; no indicator may describe a borrower as absconding, a defaulter or fraudulent (FR-RSK-07).
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.common.clock import business_today
from app.models.engagement import Grievance
from app.models.loans import LoanAccount, RepaymentSchedule, ScheduleInstalment
from app.models.ops import Case, CaseFollowUp, RiskIndicator, RiskRule
from app.models.students import EmploymentRecord, Student, StudentAddress

OPEN_STATES = ("OPEN", "IN_REVIEW")
REVIEWED_STATES = ("ACTIONED", "DISMISSED", "OVERRIDDEN")
NO_CONTACT = ("NO_ANSWER", "WRONG_NUMBER", "MESSAGE_LEFT", "UNREACHABLE")
DISPUTE_CATS = ("AMOUNT_DISPUTE", "ADDRESS_DISPUTE", "DATA_CORRECTION")
OPEN_GRV = ("SUBMITTED", "ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION")
GRAD = ("GRADUATED", "EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "FURTHER_STUDY", "UNKNOWN")
BANNED_WORDS = ("abscond", "defaulter", "fraud")


def active_rules(db, tenant_id=None) -> dict[str, RiskRule]:
    out: dict[str, RiskRule] = {}
    stmt = select(RiskRule).where(RiskRule.status == "ACTIVE")
    if tenant_id is not None:
        stmt = stmt.where(RiskRule.tenant_id == tenant_id)
    for r in db.execute(stmt.order_by(RiskRule.version)).scalars():
        out[r.code] = r
    return out


def _ev(fact, value, source, as_of=None):
    return {"fact": fact, "value": None if value is None else str(value), "source": source,
            "as_of": as_of.isoformat() if hasattr(as_of, "isoformat") else as_of}


def _loans(db, tid):
    return db.execute(select(LoanAccount).where(LoanAccount.tenant_id == tid, LoanAccount.link_status == "LINKED",
                                                LoanAccount.student_id.isnot(None))).scalars().all()


def rule_hits(db, rule: RiskRule, today=None) -> list[dict]:
    """Return candidate hits {student_id, loan_id, bank_org_id, key, title, explanation, evidence, severity}."""
    today = today or business_today()
    p = rule.params or {}
    hits = []
    code = rule.code
    if code == "REPAYMENT_OVERDUE":
        for lo in _loans(db, rule.tenant_id):
            if lo.sync_state == "CURRENT" and lo.dpd is not None and lo.dpd >= int(p.get("min_dpd", 1)):
                sev = "HIGH" if lo.dpd >= int(p.get("high_dpd", 61)) else rule.severity
                hits.append(dict(student_id=lo.student_id, loan_id=lo.id, bank_org_id=lo.bank_org_id,
                                 key=str(lo.id), severity=sev,
                                 title=f"Instalment overdue {lo.dpd} days on {lo.bank_loan_ref}",
                                 explanation=(f"The bank-confirmed schedule shows an unpaid instalment {lo.dpd} days "
                                              f"past its due date (bucket {lo.dpd_bucket}). Review the bank data "
                                              f"before any contact."),
                                 evidence=[_ev("Display DPD", lo.dpd, "DAPRO evaluation of bank schedule", lo.status_evaluated_at),
                                           _ev("Overdue amount (INR)", lo.overdue_amount, lo.source_system, lo.last_synced_at),
                                           _ev("Bank sync state", lo.sync_state, lo.source_system, lo.last_synced_at)]))
    elif code == "REPEATED_OVERDUE":
        n = int(p.get("min_overdue_instalments", 3))
        for lo in _loans(db, rule.tenant_id):
            if lo.sync_state != "CURRENT":
                continue
            cnt = db.execute(select(func.count()).select_from(ScheduleInstalment).join(
                RepaymentSchedule, RepaymentSchedule.id == ScheduleInstalment.schedule_id).where(
                ScheduleInstalment.loan_id == lo.id, RepaymentSchedule.is_current.is_(True),
                ScheduleInstalment.status.in_(["OVERDUE", "PARTIALLY_PAID"]))).scalar()
            if cnt >= n:
                hits.append(dict(student_id=lo.student_id, loan_id=lo.id, bank_org_id=lo.bank_org_id, key=str(lo.id),
                                 severity=rule.severity, title=f"{cnt} instalments overdue or part-paid on {lo.bank_loan_ref}",
                                 explanation=(f"{cnt} instalments are confirmed by the bank as overdue or partially "
                                              f"paid (threshold {n}). Priority review is suggested; a person decides."),
                                 evidence=[_ev("Overdue or part-paid instalments", cnt, lo.source_system, lo.last_synced_at),
                                           _ev("Threshold", n, f"Rule {rule.code} v{rule.version}")]))
    elif code == "DATA_STALE":
        for lo in _loans(db, rule.tenant_id):
            if lo.sync_state in ("STALE", "FAILED"):
                hits.append(dict(student_id=lo.student_id, loan_id=lo.id, bank_org_id=lo.bank_org_id, key=str(lo.id),
                                 severity=rule.severity, title=f"Bank data {lo.sync_state.lower()} for {lo.bank_loan_ref}",
                                 explanation=("The last successful bank synchronization is older than the agreed "
                                              "interval. Repayment status is shown as UNKNOWN; no repayment "
                                              "conclusion should be drawn."),
                                 evidence=[_ev("Last successful sync", lo.last_synced_at, lo.source_system),
                                           _ev("Sync state", lo.sync_state, lo.source_system)]))
    return hits + _more_hits(db, rule, today)


def _bank_of(db, student_id):
    return db.execute(select(LoanAccount.bank_org_id).where(LoanAccount.student_id == student_id,
                                                            LoanAccount.link_status == "LINKED").limit(1)).scalar()


def _borrowers(db, tid):
    ids = select(LoanAccount.student_id).where(LoanAccount.tenant_id == tid, LoanAccount.link_status == "LINKED")
    return db.execute(select(Student).where(Student.tenant_id == tid, Student.id.in_(ids))).scalars().all()


def _more_hits(db, rule, today) -> list[dict]:
    p = rule.params or {}
    hits = []
    code = rule.code
    if code == "ADDRESS_UPDATE_NEEDED":
        for s in _borrowers(db, rule.tenant_id):
            addrs = db.execute(select(StudentAddress).where(StudentAddress.student_id == s.id,
                                                            StudentAddress.is_current.is_(True))).scalars().all()
            bad = [a for a in addrs if a.verification in ("FAILED", "DISPUTED")]
            cur_ok = any(a.kind == "CURRENT" and a.verification == "VERIFIED" for a in addrs)
            if bad or (s.lifecycle_status in GRAD and not cur_ok and not any(a.kind == "CURRENT" for a in addrs)):
                reason = (f"Current address verification is {bad[0].verification}" if bad
                          else "No current address is on record since graduation")
                hits.append(dict(student_id=s.id, loan_id=None, bank_org_id=_bank_of(db, s.id), key=str(s.id),
                                 severity=rule.severity, title="Address update or verification needed",
                                 explanation=f"{reason}. Request a borrower update through approved channels.",
                                 evidence=[_ev("Address state", bad[0].verification if bad else "MISSING",
                                               bad[0].source_type if bad else "DAPRO records",
                                               bad[0].verified_at or bad[0].created_at if bad else None)]))
    elif code == "CONTACT_UNSUCCESSFUL":
        n, win = int(p.get("min_attempts", 3)), int(p.get("window_days", 30))
        since = datetime.now(UTC) - timedelta(days=win)
        rows = db.execute(select(Case, func.count(CaseFollowUp.id)).join(CaseFollowUp, CaseFollowUp.case_id == Case.id)
                          .where(CaseFollowUp.outcome.in_(NO_CONTACT), CaseFollowUp.contacted_at >= since,
                                 Case.tenant_id == rule.tenant_id,
                                 Case.status.notin_(["RESOLVED", "CLOSED"])).group_by(Case.id)).all()
        for case, cnt in rows:
            if cnt >= n:
                hits.append(dict(student_id=case.student_id, loan_id=case.loan_id, bank_org_id=case.bank_org_id,
                                 key=str(case.student_id), severity=rule.severity,
                                 title=f"{cnt} documented contact attempts without contact",
                                 explanation=(f"Case {case.case_ref} records {cnt} contact attempts in {win} days "
                                              f"without reaching the borrower. Manager review is suggested; this is "
                                              f"an operational signal only and says nothing about intent."),
                                 evidence=[_ev("Unsuccessful attempts", cnt, f"Case {case.case_ref} follow-ups"),
                                           _ev("Window (days)", win, f"Rule {rule.code} v{rule.version}")]))
    elif code == "EMPLOYMENT_UPDATE_DUE":
        days = int(p.get("days_after_graduation", 180))
        from app.models.students import AcademicRecord
        for s in _borrowers(db, rule.tenant_id):
            if s.lifecycle_status not in GRAD:
                continue
            ac = db.execute(select(AcademicRecord).where(AcademicRecord.student_id == s.id,
                                                         AcademicRecord.is_current.is_(True))).scalar()
            done = ac.actual_completion if ac else None
            if not done or done > today - timedelta(days=days):
                continue
            has = db.execute(select(func.count()).where(EmploymentRecord.student_id == s.id,
                                                        EmploymentRecord.is_current.is_(True))).scalar()
            if not has:
                hits.append(dict(student_id=s.id, loan_id=None, bank_org_id=_bank_of(db, s.id), key=str(s.id),
                                 severity=rule.severity, title="Post-study status update due",
                                 explanation=(f"Course completed on {done.isoformat()} and no post-study status has "
                                              f"been recorded. A neutral, voluntary update request may be sent."),
                                 evidence=[_ev("Course completion", done, ac.source if ac else "college"),
                                           _ev("Window (days)", days, f"Rule {rule.code} v{rule.version}")]))
    elif code == "MORATORIUM_ENDING":
        days = int(p.get("days_before", 45))
        for lo in _loans(db, rule.tenant_id):
            if lo.moratorium_end and today <= lo.moratorium_end <= today + timedelta(days=days):
                due = db.execute(select(func.count()).where(ScheduleInstalment.loan_id == lo.id,
                                                            ScheduleInstalment.due_date <= today)).scalar()
                if not due:
                    hits.append(dict(student_id=lo.student_id, loan_id=lo.id, bank_org_id=lo.bank_org_id,
                                     key=str(lo.id), severity=rule.severity,
                                     title=f"Moratorium ends {lo.moratorium_end.isoformat()} on {lo.bank_loan_ref}",
                                     explanation=("The moratorium ends soon and no instalment has fallen due yet. "
                                                  "Engage the student before the first EMI to confirm readiness."),
                                     evidence=[_ev("Moratorium end", lo.moratorium_end, lo.source_system, lo.last_synced_at),
                                               _ev("First EMI (bank)", lo.repayment_start, lo.source_system)]))
    elif code == "DISPUTED_RECORD":
        for g in db.execute(select(Grievance).where(Grievance.tenant_id == rule.tenant_id,
                                                    Grievance.category.in_(DISPUTE_CATS),
                                                    Grievance.status.in_(OPEN_GRV))).scalars():
            hits.append(dict(student_id=g.student_id, loan_id=g.loan_id, bank_org_id=_bank_of(db, g.student_id),
                             key=str(g.student_id), severity=rule.severity, title=f"Open dispute {g.ref}",
                             explanation=(f"The borrower has an open {g.category.replace('_', ' ').lower()} "
                                          f"({g.ref}). Pause affected outreach and route to the grievance owner."),
                             evidence=[_ev("Grievance", g.ref, "DAPRO grievance register", g.created_at),
                                       _ev("Status", g.status, "DAPRO grievance register")]))
    return hits


def assert_neutral(text: str) -> None:
    low = text.lower()
    for w in BANNED_WORDS:
        if w in low:
            raise ValueError(f"Non-neutral wording in indicator: {w}")


def evaluate_tenant(db, tenant_id, today=None) -> dict:
    """Run all active rules. Returns counts. Caller commits."""
    stats = {"created": 0, "unchanged": 0, "superseded": 0}
    now = datetime.now(UTC)
    for code, rule in active_rules(db, tenant_id).items():
        hits = rule_hits(db, rule, today)
        keys = set()
        for h in hits:
            key = f"{code}:{h['key']}"
            keys.add(key)
            if h["student_id"] is None:
                continue
            recent = now - timedelta(days=30)
            existing = db.execute(select(RiskIndicator.id).where(
                RiskIndicator.tenant_id == tenant_id, RiskIndicator.dedupe_key == key,
                (RiskIndicator.status.in_(OPEN_STATES)) | (
                    RiskIndicator.status.in_(REVIEWED_STATES) & (RiskIndicator.updated_at >= recent))).limit(1)).scalar()
            if existing:
                stats["unchanged"] += 1
                continue
            assert_neutral(h["title"] + " " + h["explanation"])
            db.add(RiskIndicator(
                tenant_id=tenant_id, student_id=h["student_id"], loan_id=h["loan_id"], bank_org_id=h["bank_org_id"],
                rule_id=rule.id, rule_code=code, rule_version=rule.version, category=rule.category,
                severity=h["severity"], title=h["title"], explanation=h["explanation"], evidence=h["evidence"],
                input_snapshot={"params": rule.params, "evaluated_at": now.isoformat(),
                                "recommended_action": rule.recommended_action},
                status="OPEN", dedupe_key=key))
            stats["created"] += 1
        for ind in db.execute(select(RiskIndicator).where(RiskIndicator.tenant_id == tenant_id,
                                                          RiskIndicator.rule_code == code,
                                                          RiskIndicator.status.in_(OPEN_STATES))).scalars():
            if ind.dedupe_key not in keys:
                ind.status = "SUPERSEDED"
                ind.input_snapshot = {**(ind.input_snapshot or {}), "superseded_at": now.isoformat(),
                                      "superseded_note": "Triggering condition no longer present at re-evaluation."}
                stats["superseded"] += 1
    db.flush()
    return stats


def dry_run(db, rule: RiskRule) -> dict:
    hits = rule_hits(db, rule)
    return {"rule": rule.code, "version": rule.version, "would_trigger": len(hits),
            "sample": [{"title": h["title"], "severity": h["severity"]} for h in hits[:10]]}
