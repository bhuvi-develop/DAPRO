"""Seed stage 4: risk indicators, cases, follow-ups, field visits, commitments, communications, grievances.

Operations are performed through the real services (so business rules, events and audit apply) under a
SeedContext whose clock is backdated, giving a chronological, internally consistent history.
"""
import dataclasses
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import event, select

from app.core import audit
from app.core.authz import build_context
from app.core.context import RequestContext
from app.models.engagement import Communication
from app.models.iam import User
from app.models.loans import Guarantor, LoanAccount, MockBankRecord, RepaymentTransaction
from app.models.ops import Case, PaymentCommitment, RiskIndicator
from app.models.students import Consent, ContactPreference, Student, StudentAddress
from app.seed.data import RNG

NOW = datetime.now(UTC)


@dataclasses.dataclass
class SeedContext(RequestContext):
    clock: datetime | None = None

    def audit(self, action, *, target_type=None, target_id=None, target_label=None, outcome="SUCCESS",
              payload=None, purpose=None):
        return audit.write(self.db, tenant_id=self.tenant_id, action=action, outcome=outcome, actor_id=self.user_id,
                           actor_label=self.user_name, actor_role=self.role, org_id=self.org_id,
                           target_type=target_type, target_id=target_id, target_label=target_label,
                           purpose=purpose, correlation_id=self.correlation_id or None, payload=payload,
                           occurred_at=self.clock)

    def commit(self):
        self.db.flush()


class Clock:
    def __init__(self, db):
        self.db = db
        self.t = NOW
        event.listen(db, "before_flush", self._stamp)

    def _stamp(self, session, ctx, instances):
        for obj in session.new:
            for attr in ("created_at", "updated_at", "generated_at", "received_at"):
                if hasattr(obj, attr) and getattr(obj, attr, None) is None:
                    setattr(obj, attr, self.t)

    def set(self, t, *ctxs):
        self.t = min(t, NOW)
        for c in ctxs:
            c.clock = self.t

    def close(self):
        event.remove(self.db, "before_flush", self._stamp)


def make_ctx(db, user: User) -> SeedContext:
    base = build_context(db, user)
    return SeedContext(**{f.name: getattr(base, f.name) for f in dataclasses.fields(base)}, clock=NOW)


def days_ago(d: float, hour: int = 5) -> datetime:
    t = NOW - timedelta(days=d)
    return min(t.replace(hour=hour, minute=RNG.randint(0, 59), second=0, microsecond=0), NOW - timedelta(minutes=5))


def profile_of(db, loan) -> str | None:
    return db.execute(select(MockBankRecord.profile).where(MockBankRecord.bank_loan_ref == loan.bank_loan_ref,
                                                           MockBankRecord.tenant_id == loan.tenant_id)).scalar()


def backdate_indicators(db, tid):
    for ind in db.execute(select(RiskIndicator).where(RiskIndicator.tenant_id == tid)).scalars():
        loan = db.get(LoanAccount, ind.loan_id) if ind.loan_id else None
        if ind.rule_code in ("REPAYMENT_OVERDUE", "REPEATED_OVERDUE") and loan and loan.dpd:
            ind.generated_at = days_ago(max(min(loan.dpd - 1, 45), 0), 1)
        else:
            ind.generated_at = days_ago(RNG.randint(0, 20), 1)
        ind.updated_at = ind.generated_at


def _spaced(t0: datetime, n: int, until: datetime | None = None) -> list[datetime]:
    span = max(((until or NOW) - timedelta(hours=2)) - t0, timedelta(hours=n + 1))
    return [min(t0 + span * (k + 1) / (n + 1), NOW - timedelta(minutes=30)) for k in range(n)]


def _fix_last_follow_up(db, case_id, t):
    from app.models.ops import CaseFollowUp

    f = db.execute(select(CaseFollowUp).where(CaseFollowUp.case_id == case_id)
                   .order_by(CaseFollowUp.contacted_at.desc()).limit(1)).scalar()
    if f:
        f.contacted_at = t


def work_case(db, clock, c: Case, plan: str, owner_ctx, mgr_ctx, close_ctx, until=None):
    """Drive a case to the planned state through the real service rules."""
    from app.modules.cases import service as cs

    t0 = c.created_at
    if plan == "NEW":
        return
    clock.set(t0 + timedelta(hours=2), mgr_ctx)
    cs.assign(mgr_ctx, c, owner_ctx.user_id, commit=False)
    if plan == "ASSIGNED":
        return
    steps = {"ATTEMPTED": ["NO_ANSWER"], "ATTEMPTED_3": ["NO_ANSWER", "WRONG_NUMBER", "NO_ANSWER", "NO_ANSWER"],
             "ESTABLISHED": ["NO_ANSWER", "CONTACT_ESTABLISHED"], "UPDATE_PENDING": ["CONTACT_ESTABLISHED"],
             "ESCALATED": ["NO_ANSWER", "NO_ANSWER", "NO_ANSWER"], "RESOLVED_INFO": ["CONTACT_ESTABLISHED"],
             "CLOSED_INFO": ["NO_ANSWER", "BORROWER_UPDATE_RECEIVED"], "PAID": ["NO_ANSWER", "CONTACT_ESTABLISHED"]}
    outcomes = steps.get(plan, [])
    start = t0 + timedelta(hours=3)
    if plan in ("ATTEMPTED_3", "ESCALATED"):
        start = max(start, NOW - timedelta(days=18))
    times = _spaced(start, len(outcomes) + 2, until)
    notes = {"NO_ANSWER": "Called registered mobile; no answer. Left no voicemail as per conduct policy.",
             "WRONG_NUMBER": "Number answered by another person who does not know the borrower. Number flagged.",
             "CONTACT_ESTABLISHED": "Spoke to borrower. Confirmed identity and shared bank-confirmed due details.",
             "BORROWER_UPDATE_RECEIVED": "Borrower shared updated address and employer details by email."}
    for k, oc in enumerate(outcomes):
        clock.set(times[k], owner_ctx)
        cs.add_follow_up(owner_ctx, c, "PHONE" if oc != "BORROWER_UPDATE_RECEIVED" else "EMAIL", oc, notes[oc],
                         contacted_at=times[k],
                         next_follow_up_on=(times[k] + timedelta(days=5)).date() if k == len(outcomes) - 1 else None)
    last = times[len(outcomes)]
    if plan == "UPDATE_PENDING":
        clock.set(last, owner_ctx)
        cs.transition(owner_ctx, c, "BORROWER_UPDATE_PENDING", "Borrower will send employment proof and new address")
    elif plan == "ESCALATED":
        clock.set(last, mgr_ctx)
        cs.transition(mgr_ctx, c, "ESCALATED", "Three unsuccessful attempts; manager review requested. No inference drawn.")
    elif plan in ("RESOLVED_INFO", "CLOSED_INFO"):
        clock.set(last, mgr_ctx)
        cs.transition(mgr_ctx, c, "RESOLVED", "Borrower contact details updated and verified; bank informed.",
                      resolution_type="BORROWER_INFORMATION_UPDATED")
        if plan == "CLOSED_INFO":
            clock.set(times[-1], close_ctx)
            cs.transition(close_ctx, c, "CLOSED", "Reviewed resolution evidence; closing.")


def open_case_from_indicator(db, clock, ind, ctx, priority="MEDIUM"):
    from app.modules.risk.service import decide

    t0 = min(ind.generated_at + timedelta(hours=20), NOW - timedelta(hours=6))
    clock.set(t0, ctx)
    decide(ctx, ind, "CREATE_CASE", "Bank-confirmed overdue verified against latest snapshot; follow-up needed.",
           priority=priority)
    c = db.get(Case, ind.case_id)
    c.created_at = t0
    c.due_on = (t0 + timedelta(days={"CRITICAL": 2, "HIGH": 5, "MEDIUM": 10, "LOW": 20}[priority])).date()
    return c

ANB_PLAN = ["NEW", "NEW", "ASSIGNED", "ASSIGNED", "ATTEMPTED", "ATTEMPTED_3", "ATTEMPTED_3", "ATTEMPTED",
            "ESTABLISHED", "ESTABLISHED", "ESTABLISHED", "UPDATE_PENDING", "UPDATE_PENDING", "ESCALATED",
            "ESCALATED", "RESOLVED_INFO", "CLOSED_INFO", "CLOSED_INFO"]
MFB_PLAN = ["NEW", "ASSIGNED", "ATTEMPTED", "ESTABLISHED", "ESCALATED", "RESOLVED_INFO"]


def _indicators(db, tid, bank_id, rule, n):
    rows = db.execute(select(RiskIndicator).join(LoanAccount, LoanAccount.id == RiskIndicator.loan_id)
                      .where(RiskIndicator.tenant_id == tid, RiskIndicator.rule_code == rule,
                             RiskIndicator.status == "OPEN", LoanAccount.bank_org_id == bank_id)
                      .order_by(LoanAccount.dpd.desc().nullslast())).scalars().all()
    return rows[:n]


def seed_cases(db, F, clock, C) -> dict:
    tid, units = F["tenant"].id, F["units"]
    chennai = {units["ANB-ANN"].id, units["ANB-TNG"].id}
    made = {"anb": [], "mfb": [], "field": []}
    inds = _indicators(db, tid, F["orgs"]["ANB"].id, "REPAYMENT_OVERDUE", len(ANB_PLAN) + 6)
    for k, ind in enumerate(inds[:len(ANB_PLAN)]):
        loan = db.get(LoanAccount, ind.loan_id)
        prio = "CRITICAL" if (loan.dpd or 0) > 180 else ("HIGH" if (loan.dpd or 0) > 60 else "MEDIUM")
        c = open_case_from_indicator(db, clock, ind, C["head"], prio)
        owner = C["meena"] if (loan.branch_unit_id in chennai and k % 3 == 0) else (
            C["inv"] if k % 2 else C["head"])
        if owner is C["head"] and ANB_PLAN[k] in ("RESOLVED_INFO", "CLOSED_INFO", "ESCALATED"):
            owner = C["inv"]
        work_case(db, clock, c, ANB_PLAN[k], owner, C["head"], C["ravi"])
        made["anb"].append(c)
    for k, ind in enumerate(inds[len(ANB_PLAN):]):  # field cases: assigned to field officers
        c = open_case_from_indicator(db, clock, ind, C["head"], "HIGH")
        work_case(db, clock, c, "ASSIGNED", C["karthik"] if k % 2 == 0 else C["nithya"], C["head"], C["ravi"])
        made["field"].append(c)
    for k, ind in enumerate(_indicators(db, tid, F["orgs"]["MFB"].id, "REPAYMENT_OVERDUE", len(MFB_PLAN))):
        c = open_case_from_indicator(db, clock, ind, C["mfbm"], "MEDIUM")
        work_case(db, clock, c, MFB_PLAN[k], C["mfbops"] if k % 2 else C["mfbm"], C["mfbm"], C["mfbops"])
        made["mfb"].append(c)
    for ind in db.execute(select(RiskIndicator).where(RiskIndicator.tenant_id == tid,
                                                      RiskIndicator.rule_code == "MORATORIUM_ENDING",
                                                      RiskIndicator.status == "OPEN")).scalars().all()[:2]:
        loan = db.get(LoanAccount, ind.loan_id)
        if loan.bank_org_id == F["orgs"]["ANB"].id:
            c = open_case_from_indicator(db, clock, ind, C["head"], "LOW")
            work_case(db, clock, c, "ASSIGNED", C["inv"], C["head"], C["ravi"])
    seed_paid_case(db, F, clock, C)
    return made


def seed_paid_case(db, F, clock, C):
    """Recovered loan: case resolved only on a bank-confirmed transaction (BR-11), commitment matched to it."""
    from app.modules.cases import service as cs

    tid = F["tenant"].id
    loan = None
    for lo in db.execute(select(LoanAccount).where(LoanAccount.tenant_id == tid,
                                                   LoanAccount.bank_org_id == F["orgs"]["ANB"].id,
                                                   LoanAccount.link_status == "LINKED")).scalars():
        if profile_of(db, lo) == "RECOVERED" and lo.repayment_status == "CURRENT":
            loan = lo
            break
    if loan is None:
        return
    txn = db.execute(select(RepaymentTransaction).where(RepaymentTransaction.loan_id == loan.id,
                                                        RepaymentTransaction.kind == "PAYMENT")
                     .order_by(RepaymentTransaction.amount.desc()).limit(1)).scalar()
    t0 = datetime.combine(txn.posted_on, datetime.min.time(), tzinfo=UTC) - timedelta(days=20)
    clock.set(t0, C["head"])
    c = cs.create_case(C["head"], student_id=loan.student_id, loan_id=loan.id, category="REPAYMENT_FOLLOW_UP",
                       reason="Two consecutive instalments unpaid per bank feed", priority="HIGH",
                       next_action="Contact borrower and confirm repayment plan")
    c.created_at, c.due_on = t0, (t0 + timedelta(days=5)).date()
    posted = datetime.combine(txn.posted_on, datetime.min.time(), tzinfo=UTC) + timedelta(days=2, hours=6)
    work_case(db, clock, c, "ESTABLISHED", C["inv"], C["head"], C["ravi"], until=posted)
    db.add(PaymentCommitment(tenant_id=tid, case_id=c.id, loan_id=loan.id, amount=txn.amount,
                             promised_date=txn.posted_on - timedelta(days=2), source="BORROWER_REPORTED",
                             status="BANK_CONFIRMED", bank_txn_ref=txn.bank_txn_ref, recorded_by=C["inv"].user_id,
                             notes="Borrower said salary credit expected; matched later to bank transaction",
                             created_at=t0 + timedelta(days=3)))
    clock.set(posted, C["head"])
    cs.transition(C["head"], c, "RESOLVED", "Bank feed confirms lump-sum payment clearing overdue instalments.",
                  resolution_type="PAYMENT_CONFIRMED", bank_txn_ref=txn.bank_txn_ref)
    clock.set(posted + timedelta(days=1), C["ravi"])
    cs.transition(C["ravi"], c, "CLOSED", "Verified bank transaction reference; closing.")

VISIT_PLAN = [("COMPLETED", False, "Met borrower at residence. Borrower confirmed employment and will contact bank."),
              ("NO_CONTACT", False, "No one available at address. Neighbour confirmed family resides here."),
              ("ADDRESS_NOT_FOUND", False, "Door number does not exist on this street. Address needs verification."),
              ("BORROWER_UNAVAILABLE", True, "Borrower relative became aggressive; officer left immediately."),
              ("RESCHEDULE_REQUESTED", False, "Borrower requested visit next week after exams of sibling."),
              ("COMPLETED", False, "Borrower present; shared updated phone number and current employer.")]


def seed_visits(db, F, clock, C, field_cases):
    from app.modules.cases import service as cs
    from app.modules.field import service as fs

    k = 0
    if len(field_cases) > 1:
        field_cases[1].priority = "CRITICAL"
    for c in field_cases:
        officer = C["karthik"] if c.owner_id == C["karthik"].user_id else C["nithya"]
        for j in range(2):
            outcome, incident, note = VISIT_PLAN[k % len(VISIT_PLAN)]
            k += 1
            t = c.created_at + timedelta(days=1 + j * 3, hours=4)
            clock.set(t, officer)
            future = j == 1 and k % 3 == 0
            v = fs.create_visit(officer, c.id, "Verify contact details and share bank-confirmed status",
                                scheduled_for=(NOW + timedelta(days=2)) if future else t)
            if future:
                continue
            fs.check(officer, v.id, "in")
            fs.check(officer, v.id, "out")
            fs.submit(officer, v.id, outcome, note, borrower_present=outcome == "COMPLETED", safety_incident=incident,
                      incident_notes="Officer withdrew; no confrontation. Reported to manager." if incident else None,
                      client_draft_id=f"seed-{c.case_ref}-{j}")
            v.check_in_at, v.check_out_at, v.visited_at = t, t + timedelta(minutes=25), t
            _fix_last_follow_up(db, c.id, t + timedelta(minutes=30))
            if outcome == "COMPLETED" and j == 0:
                clock.set(t + timedelta(minutes=40), officer)
                cs.add_commitment(officer, c, Decimal(str(c_amount(db, c))), (NOW + timedelta(days=12)).date(),
                                  "Borrower said salary is credited on the 10th")
            if v.review_status == "PENDING" and not incident:
                clock.set(t + timedelta(days=1), C["head"])
                fs.review(C["head"], v.id, "APPROVED" if j == 0 else "RETURNED",
                          "Report is complete and conduct was appropriate." if j == 0
                          else "Please add who was present and what was shared.")


def c_amount(db, c) -> Decimal:
    loan = db.get(LoanAccount, c.loan_id) if c.loan_id else None
    return (loan.emi_amount if loan and loan.emi_amount else Decimal("5000.00"))


def seed_decisions(db, F, clock, C):
    from app.modules.risk.service import assign, decide

    tid = F["tenant"].id
    open_inds = lambda rule: db.execute(select(RiskIndicator).where(  # noqa: E731
        RiskIndicator.tenant_id == tid, RiskIndicator.rule_code == rule, RiskIndicator.status == "OPEN",
        RiskIndicator.bank_org_id == F["orgs"]["ANB"].id)).scalars().all()
    for ind in open_inds("ADDRESS_UPDATE_NEEDED")[:2]:
        clock.set(ind.generated_at + timedelta(days=1), C["head"])
        decide(C["head"], ind, "DISMISS", "Borrower already submitted a new address; verification task in progress.")
    for ind in open_inds("EMPLOYMENT_UPDATE_DUE")[:2]:
        clock.set(ind.generated_at + timedelta(days=1), C["head"])
        decide(C["head"], ind, "CONFIRM_FOR_FOLLOW_UP", "Send neutral post-study update request via college channel.")
    for ind in open_inds("REPEATED_OVERDUE")[:1]:
        clock.set(ind.generated_at + timedelta(days=1), C["head"])
        decide(C["head"], ind, "OVERRIDE_SEVERITY", "Bank confirms restructure discussion in progress; lower priority.",
               override_severity="MEDIUM")
    for ind in open_inds("REPAYMENT_OVERDUE")[:3]:
        clock.set(ind.generated_at + timedelta(hours=6), C["head"])
        assign(C["head"], ind, C["meena"].user_id)


def make_borrowers(db, F, made) -> list:
    from app.seed.foundation import add_user

    tid, out, used = F["tenant"].id, [], set()
    picks = []
    estab = [c for c in made["anb"] if c.status == "CONTACT_ESTABLISHED"]
    if estab:
        picks.append(db.get(Student, estab[0].student_id))
    current = db.execute(select(Student).join(LoanAccount, LoanAccount.student_id == Student.id)
                         .where(Student.tenant_id == tid, LoanAccount.repayment_status == "CURRENT",
                                Student.college_org_id == F["orgs"]["NBIT"].id)).scalars().first()
    abroad = db.execute(select(Student).join(StudentAddress, StudentAddress.student_id == Student.id)
                        .join(LoanAccount, LoanAccount.student_id == Student.id)
                        .where(Student.tenant_id == tid, StudentAddress.country != "IN",
                               StudentAddress.is_current.is_(True))).scalars().first()
    for s in [p for p in picks + [current, abroad] if p is not None]:
        if s.id in used:
            continue
        used.add(s.id)
        email = f"{s.first_name.lower()}.borrower@student.demo"
        n = 2
        while db.execute(select(User.id).where(User.tenant_id == tid, User.email == email)).scalar():
            email = f"{s.first_name.lower()}{n}.borrower@student.demo"
            n += 1
        org = F["orgs"]["NBIT"] if s.college_org_id == F["orgs"]["NBIT"].id else F["orgs"]["RCE"]
        out.append(add_user(db, tid, org, F["roles"], "BORROWER", email, s.full_name, "Borrower", student_id=s.id))
    return out


def seed_comms(db, F, clock, C):
    from app.modules.comms.service import dispatch, send

    tid = F["tenant"].id
    loans = db.execute(select(LoanAccount).where(LoanAccount.tenant_id == tid, LoanAccount.link_status == "LINKED",
                                                 LoanAccount.next_due_date.isnot(None))
                       .order_by(LoanAccount.bank_loan_ref)).scalars().all()
    anb = [lo for lo in loans if lo.bank_org_id == F["orgs"]["ANB"].id]
    mfb = [lo for lo in loans if lo.bank_org_id == F["orgs"]["MFB"].id]

    def go(ctx, lo, code, d, hour=5, **kw):
        t = days_ago(d, hour)
        clock.set(t, ctx)
        return send(ctx, student_id=lo.student_id, template_code=code, now=t, commit=False, **kw)

    for i, lo in enumerate(anb[:12]):
        go(C["ravi"], lo, "EMI_REMINDER" if i % 3 else "EMI_REMINDER_SMS", 1 + i % 9)
    for i, lo in enumerate(mfb[:5]):
        go(C["mfbops"], lo, "EMI_REMINDER", 2 + i)
    go(C["ravi"], anb[13], "EMI_REMINDER", 2, hour=17)  # 22:xx IST: blocked by quiet hours
    withdrawn = db.execute(select(Consent.student_id).where(Consent.tenant_id == tid,
                                                            Consent.withdrawn_at.isnot(None))).scalars().all()
    for lo in [lo for lo in anb + mfb if lo.student_id in withdrawn][:2]:
        go(C["ravi"] if lo.bank_org_id == F["orgs"]["ANB"].id else C["mfbops"], lo, "CONTACT_UPDATE_REQUEST", 4)
    opted = db.execute(select(ContactPreference.student_id).where(ContactPreference.tenant_id == tid,
                                                                  ContactPreference.channel == "SMS",
                                                                  ContactPreference.allowed.is_(False))).scalars().all()
    for lo in [lo for lo in anb if lo.student_id in opted][:1]:
        go(C["ravi"], lo, "EMI_REMINDER_SMS", 3)
    for lo in anb[20:23]:
        go(C["ravi"], lo, "POST_STUDY_UPDATE", 6)
    bad = db.get(Student, anb[24].student_id)
    bad.primary_email = f"{bad.first_name.lower()}.{bad.last_name.lower()}@oldcampus.invalid"
    from app.models.students import StudentContact
    for sc in db.execute(select(StudentContact).where(StudentContact.student_id == bad.id,
                                                      StudentContact.kind == "EMAIL")).scalars():
        sc.value, sc.verification = bad.primary_email, "UNVERIFIED"
    go(C["ravi"], anb[24], "CONTACT_UPDATE_REQUEST", 5)
    for permitted in (True, False):
        g = db.execute(select(Guarantor).join(LoanAccount, LoanAccount.id == Guarantor.loan_id)
                       .where(Guarantor.tenant_id == tid, Guarantor.communication_permitted.is_(permitted),
                              LoanAccount.bank_org_id == F["orgs"]["ANB"].id,
                              LoanAccount.repayment_status == "OVERDUE")).scalars().first()
        if g:
            lo = db.get(LoanAccount, g.loan_id)
            go(C["ravi"], lo, "GUARANTOR_NOTICE", 3, recipient_type="GUARANTOR", guarantor_id=g.id,
               variables={"name": g.full_name, "agreement_ref": g.agreement_ref})
    dispatch(db)
    for c in db.execute(select(Communication).where(Communication.tenant_id == tid,
                                                    Communication.status.in_(["DELIVERED", "FAILED"]))).scalars():
        c.sent_at = c.created_at + timedelta(minutes=2)
        c.delivered_at = c.created_at + timedelta(minutes=4) if c.status == "DELIVERED" else None


def _grv(db, clock, ctx, d, **kw):
    from app.modules.grievances import service as gs

    t = days_ago(d, 6)
    clock.set(t, ctx)
    g = gs.create(ctx, **kw)
    g.created_at = t
    g.due_on = (t + timedelta(days=15)).date()
    return g


def _step(clock, ctx, t, fn, *a, **kw):
    clock.set(t, ctx)
    return fn(ctx, *a, **kw)


def seed_grievances(db, F, clock, C, borrowers, made):
    from app.modules.grievances import service as gs

    B = [make_ctx(db, u) for u in borrowers]
    tid = F["tenant"].id
    if B:
        arun = db.get(Student, B[0].student_id)
        case = db.execute(select(Case).where(Case.student_id == arun.id, Case.loan_id.isnot(None),
                                             Case.status.notin_(["RESOLVED", "CLOSED"]))).scalars().first()
        loan = db.get(LoanAccount, case.loan_id) if case else db.execute(
            select(LoanAccount).where(LoanAccount.student_id == arun.id)).scalars().first()
        g = _grv(db, clock, B[0], 4, student_id=arun.id, category="AMOUNT_DISPUTE", loan_id=loan.id if loan else None,
                 subject="Reminder shows an amount I already paid",
                 description="I paid my instalment through UPI before the due date but the reminder shows it unpaid.")
        _step(clock, C["head"], g.created_at + timedelta(hours=3), gs.assign, g, C["ravi"].user_id)
        _step(clock, C["ravi"], g.created_at + timedelta(hours=5), gs.transition, g, "ACKNOWLEDGED")
        _step(clock, C["ravi"], g.created_at + timedelta(days=1), gs.transition, g, "UNDER_REVIEW")
        _step(clock, C["ravi"], g.created_at + timedelta(days=1, hours=1), gs.respond, g,
              "We are checking the payment with the bank. You will not receive reminders while this is reviewed.")
    if len(B) > 1:
        s2 = db.get(Student, B[1].student_id)
        g = _grv(db, clock, B[1], 9, student_id=s2.id, category="DATA_CORRECTION", subject="My mobile number changed",
                 description="Please update my mobile number to the new one below.", correction_field="primary_mobile",
                 correction_requested_value="+919840012345")
        admin = C["priya"] if s2.college_org_id == F["orgs"]["NBIT"].id else C["rce"]
        _step(clock, admin, g.created_at + timedelta(hours=2), gs.assign, g, admin.user_id)
        _step(clock, admin, g.created_at + timedelta(days=1), gs.transition, g, "UNDER_REVIEW")
        _step(clock, admin, g.created_at + timedelta(days=2), gs.transition, g, "RESOLVED",
              "Mobile number verified by OTP at the college office and updated.", approve_correction=True)
    if len(B) > 2:
        s3 = db.get(Student, B[2].student_id)
        g = _grv(db, clock, B[2], 1, student_id=s3.id, category="COMMUNICATION_COMPLAINT",
                 subject="Messages arrive at night in my time zone",
                 description="I live abroad and reminders reach me late at night. Please use email only.")
    field = made["field"][0] if made["field"] else None
    if field:
        g = _grv(db, clock, C["head"], 6, student_id=field.student_id, category="CONDUCT_COMPLAINT",
                 subject="Concern about the field visit manner", channel="PHONE",
                 subject_user_id=C["karthik"].user_id,
                 description="Borrower family reported that the visiting officer came at an inconvenient time.")
        _step(clock, C["head"], g.created_at + timedelta(hours=1), gs.assign, g, C["head"].user_id)
        _step(clock, C["head"], g.created_at + timedelta(hours=2), gs.transition, g, "ACKNOWLEDGED")
        _step(clock, C["head"], g.created_at + timedelta(days=1), gs.respond, g,
              "Visit logs, timing and notes requested from the officer's supervisor.", "INTERNAL")
    others = [c for c in made["anb"] if c.status in ("CONTACT_ATTEMPTED", "ASSIGNED")]
    if others:
        c = others[0]
        g = _grv(db, clock, C["ravi"], 12, student_id=c.student_id, category="AMOUNT_DISPUTE", loan_id=c.loan_id,
                 subject="Borrower disputes overdue charges", channel="EMAIL",
                 description="Borrower states the overdue amount includes an instalment already deferred.")
        _step(clock, C["ravi"], g.created_at + timedelta(hours=4), gs.assign, g, C["ravi"].user_id)
        _step(clock, C["ravi"], g.created_at + timedelta(days=1), gs.transition, g, "UNDER_REVIEW")
        _step(clock, C["ravi"], g.created_at + timedelta(days=3), gs.transition, g, "REJECTED",
              "Bank statement confirms no deferment was approved; amounts are correct.")
    stu = db.execute(select(Student).where(Student.tenant_id == tid, Student.college_org_id == F["orgs"]["NBIT"].id)
                     .order_by(Student.dapro_ref).offset(30)).scalars().first()
    g = _grv(db, clock, C["priya"], 25, student_id=stu.id, category="DATA_CORRECTION",
             subject="My email address has changed", description="Please use my new personal email address for updates.",
             correction_field="primary_email", correction_requested_value=f"{stu.first_name.lower()}.new@mail.demo")
    _step(clock, C["priya"], g.created_at + timedelta(days=1), gs.assign, g, C["priya"].user_id)
    _step(clock, C["priya"], g.created_at + timedelta(days=2), gs.transition, g, "UNDER_REVIEW")
    _step(clock, C["priya"], g.created_at + timedelta(days=4), gs.transition, g, "RESOLVED",
          "Email address updated after confirmation from the student.", approve_correction=True)
    _step(clock, C["priya"], g.created_at + timedelta(days=6), gs.transition, g, "CLOSED")
    stu2 = db.execute(select(Student).where(Student.tenant_id == tid).order_by(Student.dapro_ref).offset(55)).scalars().first()
    _grv(db, clock, C["priya"] if stu2.college_org_id == F["orgs"]["NBIT"].id else C["rce"], 21,
         student_id=stu2.id, category="OTHER", subject="Request for copy of loan statement",
         description="Student asks for a copy of the latest bank loan statement for a visa application.")


def seed_operations(db, F) -> None:
    from app.modules.risk.engine import evaluate_tenant

    tid = F["tenant"].id
    U = F["users"]
    clock = Clock(db)
    try:
        clock.set(NOW - timedelta(days=1))
        evaluate_tenant(db, tid)
        backdate_indicators(db, tid)
        db.flush()
        C = {"head": make_ctx(db, U["anb_manager_all"]), "meena": make_ctx(db, U["meena"]),
             "inv": make_ctx(db, U["investigator"]), "karthik": make_ctx(db, U["karthik"]),
             "nithya": make_ctx(db, U["field2"]), "ravi": make_ctx(db, U["ravi"]),
             "mfbm": make_ctx(db, U["mfb_manager"]), "mfbops": make_ctx(db, U["mfb_ops"]),
             "priya": make_ctx(db, U["priya"]), "rce": make_ctx(db, U["rce_admin"])}
        made = seed_cases(db, F, clock, C)
        seed_visits(db, F, clock, C, made["field"])
        seed_decisions(db, F, clock, C)
        seed_comms(db, F, clock, C)
        borrowers = make_borrowers(db, F, made)
        db.flush()
        seed_grievances(db, F, clock, C, borrowers, made)
        clock.set(NOW - timedelta(minutes=10))
        stats = evaluate_tenant(db, tid)
        audit.write(db, tenant_id=tid, action="risk.evaluated", actor_label="Scheduler (Celery beat)",
                    actor_role="SYSTEM", payload=stats, occurred_at=NOW - timedelta(minutes=10))
        db.flush()
    finally:
        clock.close()
