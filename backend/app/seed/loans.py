"""Seed stage 3: mock bank loan book, loan linkage, parties, guarantors, witnesses, then a real sync run."""
from datetime import date, datetime, timedelta

from sqlalchemy import select

from app.common.clock import business_today
from app.models.loans import Guarantor, LoanAccount, LoanParty, MockBankRecord, ReconciliationItem, Witness
from app.seed.data import RELATIONS, RNG, mobile, person

TODAY = business_today()
WEIGHTS = {"PUNCTUAL": 38, "OCCASIONAL_LATE": 14, "PARTIAL_PAYER": 8, "CHRONIC_OVERDUE": 11, "EARLY_OVERDUE": 11,
           "RECOVERED": 7, "REVERSAL": 5, "CLOSED": 6}


def _first_of_next_month(d: date) -> date:
    return date(d.year + (d.month == 12), d.month % 12 + 1, 5)


def _terms(acad, branch_code: str) -> dict:
    sanctioned = RNG.randrange(400000, 1500001, 50000)
    disbursed = int(sanctioned * RNG.uniform(0.9, 1.0) / 1000) * 1000
    start, end = acad.start_date, acad.expected_completion
    mor_end = end + timedelta(days=365)
    return {"product": "Education Loan - Domestic" if RNG.random() < 0.85 else "Education Loan - Skill",
            "scheme": RNG.choice(["Vidya Scheme (demo)", "Merit Plus (demo)", "Standard"]),
            "sanctioned": sanctioned, "disbursed": disbursed, "rate": RNG.choice([9.5, 10.0, 10.25, 10.75, 11.0, 11.5]),
            "tenure_months": RNG.choice([60, 84, 96, 120]), "sanction_date": (start - timedelta(days=20)).isoformat(),
            "disbursement_date": start.isoformat(), "moratorium_end": mor_end.isoformat(),
            "repayment_start": _first_of_next_month(mor_end).isoformat(), "branch_code": branch_code}


def _profile(student, terms) -> str:
    rs = date.fromisoformat(terms["repayment_start"])
    if rs > TODAY:
        return "STUDYING"
    weights = dict(WEIGHTS)
    if student.lifecycle_status in ("UNEMPLOYED", "UNKNOWN", "GRADUATED"):
        weights.update(CHRONIC_OVERDUE=25, EARLY_OVERDUE=18, PARTIAL_PAYER=14, PUNCTUAL=18)
    p = RNG.choices(list(weights), list(weights.values()))[0]
    if p == "CLOSED":
        if rs <= TODAY - timedelta(days=30 * 26):
            terms["tenure_months"] = 24
        else:
            p = "PUNCTUAL"
    return p


def _bank_for(F, college):
    if college.code == "NBIT":
        return (F["orgs"]["ANB"], RNG.choice(["ANB-ANN", "ANB-TNG"])) if RNG.random() < 0.62 else (F["orgs"]["MFB"], "MFB-CHC")
    return (F["orgs"]["ANB"], "ANB-RSP") if RNG.random() < 0.5 else (F["orgs"]["MFB"], "MFB-CBE")


def _ref(bank, n, year):
    return f"ANB-EDU-{year}-{n:05d}" if bank.code == "ANB" else f"MFB-SL-{year % 100:02d}-{n:04d}"


def _parties(db, F, loan: LoanAccount, student, rec_terms):
    tid = loan.tenant_id
    db.add(LoanParty(tenant_id=tid, loan_id=loan.id, student_id=student.id, party_role="APPLICANT",
                     full_name=student.full_name, relationship="Self"))
    parent_first, _, _ = person()
    parent = f"{parent_first} {student.last_name}"
    if RNG.random() < 0.6:
        db.add(LoanParty(tenant_id=tid, loan_id=loan.id, party_role="CO_APPLICANT", full_name=parent,
                         relationship=RNG.choice(["Father", "Mother"])))
    sanction = date.fromisoformat(rec_terms["sanction_date"])
    if RNG.random() < 0.72:
        g_first, g_last, _ = person()
        name = parent if RNG.random() < 0.6 else f"{g_first} {g_last}"
        permitted = RNG.random() < 0.5
        db.add(Guarantor(tenant_id=tid, loan_id=loan.id, full_name=name, relationship_to_borrower=RNG.choice(RELATIONS),
                         mobile=mobile(), email=f"{name.split()[0].lower()}.guarantor@mail.demo",
                         address_text=f"No. {RNG.randint(1, 200)}, Main Road", city=RNG.choice(["Chennai", "Madurai", "Salem"]),
                         state="Tamil Nadu", agreement_ref=f"GA-{loan.bank_loan_ref}", agreement_executed_on=sanction,
                         guarantee_scope="Full sanctioned amount including interest (as per executed agreement)",
                         guarantee_status="ACTIVE", verification="VERIFIED" if RNG.random() < 0.7 else "UNVERIFIED",
                         communication_permitted=permitted,
                         communication_basis="Clause 14, executed guarantee agreement (demo)" if permitted else None,
                         created_by=F["users"]["ravi"].id))
    for _ in range(RNG.choice([0, 1, 1, 2])):
        w_first, w_last, _ = person()
        db.add(Witness(tenant_id=tid, loan_id=loan.id, full_name=f"{w_first} {w_last}",
                       document_ref=f"LA-{loan.bank_loan_ref}", witnessed_on=sanction,
                       address_city=RNG.choice(["Chennai", "Coimbatore", "Trichy"]),
                       verification="UNVERIFIED", created_by=F["users"]["ravi"].id))


def seed_loans(db, F, students: list[dict]) -> dict:
    tid = F["tenant"].id
    counters = {"ANB": 100, "MFB": 300}
    loans, no_loan = [], []
    for row in students:
        s = row["student"]
        if row.get("recent") or row.get("duplicate"):
            continue
        if RNG.random() < 0.1:
            no_loan.append(row)
            continue
        for k in range(2 if RNG.random() < 0.08 else 1):
            bank, branch = _bank_for(F, row["college"])
            counters[bank.code] += 1
            terms = _terms(row["academic"], branch)
            if k == 1:
                terms["product"], terms["sanctioned"], terms["disbursed"] = "Education Loan - Living Expenses", 300000, 300000
            profile = _profile(s, terms)
            ref = _ref(bank, counters[bank.code], row["academic"].cohort_year)
            db.add(MockBankRecord(tenant_id=tid, bank_org_id=bank.id, branch_code=branch, bank_loan_ref=ref,
                                  bank_borrower_ref=f"{bank.code}-CIF-{counters[bank.code] * 7919:07d}",
                                  borrower_name=s.full_name, borrower_dob=s.dob, terms=terms, profile=profile))
            ops = F["users"]["ravi"] if bank.code == "ANB" else F["users"]["mfb_ops"]
            loan = LoanAccount(tenant_id=tid, bank_org_id=bank.id, student_id=s.id, college_org_id=s.college_org_id,
                               bank_loan_ref=ref, link_status="LINKED", linked_by=ops.id,
                               linked_at=datetime.fromisoformat(terms["disbursement_date"] + "T11:00:00+00:00"),
                               link_validation={"method": "BANK_REFERENCE_LOOKUP", "name_match": True, "dob_match": True,
                                                "source": "MOCK_BANK_FEED"},
                               data_origin="DEMO", sync_state="UNKNOWN", created_at=s.created_at + timedelta(days=25))
            db.add(loan)
            db.flush()
            _parties(db, F, loan, s, terms)
            loans.append((loan, profile))
    in_rep = [lo for lo, p in loans if p == "PUNCTUAL"]
    for lo in in_rep[:2]:
        rec = db.execute(select(MockBankRecord).where(MockBankRecord.bank_loan_ref == lo.bank_loan_ref)).scalar()
        rec.terms = {**rec.terms, "quirk": "DPD_MISMATCH"}
        rec.profile = "EARLY_OVERDUE"
    for lo in in_rep[2:4]:
        rec = db.execute(select(MockBankRecord).where(MockBankRecord.bank_loan_ref == lo.bank_loan_ref)).scalar()
        rec.terms = {**rec.terms, "quirk": "UNIDENTIFIED_CREDIT"}
    # Bank loans not yet linked in DAPRO: drive the Link Loan journey and the UNMATCHED reconciliation queue.
    for row in no_loan[:6]:
        s = row["student"]
        bank, branch = _bank_for(F, row["college"])
        counters[bank.code] += 1
        terms = _terms(row["academic"], branch)
        db.add(MockBankRecord(tenant_id=tid, bank_org_id=bank.id, branch_code=branch,
                              bank_loan_ref=_ref(bank, counters[bank.code], row["academic"].cohort_year),
                              bank_borrower_ref=f"{bank.code}-CIF-{counters[bank.code] * 7919:07d}",
                              borrower_name=s.full_name, borrower_dob=s.dob, terms=terms, profile=_profile(s, terms)))
    # Ambiguous link pending human review (never auto-linked): bank name differs from DAPRO name.
    for row in no_loan[6:8]:
        s = row["student"]
        bank, branch = F["orgs"]["ANB"], "ANB-ANN"
        counters["ANB"] += 1
        ref = _ref(bank, counters["ANB"], row["academic"].cohort_year)
        bank_name = f"{s.first_name} {s.last_name[0]}. {s.last_name}"
        terms = _terms(row["academic"], branch)
        db.add(MockBankRecord(tenant_id=tid, bank_org_id=bank.id, branch_code=branch, bank_loan_ref=ref,
                              bank_borrower_ref=f"ANB-CIF-{counters['ANB'] * 7919:07d}", borrower_name=bank_name,
                              borrower_dob=s.dob, terms=terms, profile=_profile(s, terms)))
        loan = LoanAccount(tenant_id=tid, bank_org_id=bank.id, student_id=s.id, college_org_id=s.college_org_id,
                           bank_loan_ref=ref, link_status="PENDING_REVIEW", data_origin="DEMO",
                           link_validation={"method": "BANK_REFERENCE_LOOKUP", "name_match": False, "dob_match": True,
                                            "bank_name": bank_name, "dapro_name": s.full_name})
        db.add(loan)
        db.flush()
        db.add(ReconciliationItem(tenant_id=tid, bank_org_id=bank.id, loan_id=loan.id, student_id=s.id,
                                  kind="AMBIGUOUS_LINK", severity="HIGH", dedupe_key=f"AMBIGUOUS_LINK:{loan.id}",
                                  summary=f"Name mismatch linking {ref}: bank '{bank_name}' vs DAPRO '{s.full_name}'",
                                  details={"bank_name": bank_name, "dapro_name": s.full_name, "dob_match": True}))
    db.flush()
    return {"loans": loans, "no_loan": no_loan}
