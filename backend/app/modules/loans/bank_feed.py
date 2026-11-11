"""Bank data adapters. Only the MOCK adapter exists: no live bank API is available (OD-06).

The mock adapter plays the role of the bank: it owns the loan book (mock_bank_records), builds the
contractual schedule, posts transactions according to a deterministic behaviour profile and
performs the BANK-SIDE payment allocation (FIFO, oldest instalment first). DAPRO only mirrors it.
"""
import hashlib
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select

from app.models.loans import MockBankRecord

SOURCE = "MOCK_BANK_FEED"
Q = Decimal("0.01")
PROFILES = ["PUNCTUAL", "OCCASIONAL_LATE", "PARTIAL_PAYER", "CHRONIC_OVERDUE", "EARLY_OVERDUE", "RECOVERED",
            "REVERSAL", "STUDYING", "CLOSED"]


@dataclass
class FeedInstalment:
    no: int
    due: date
    amount: Decimal
    principal: Decimal
    interest: Decimal
    allocated: Decimal = Decimal("0.00")
    bank_status: str = "UNPAID"


@dataclass
class FeedTxn:
    ref: str
    posted: date
    value: date
    amount: Decimal
    kind: str
    channel: str
    payment_reference: str | None = None
    reverses: str | None = None
    allocations: list = field(default_factory=list)


@dataclass
class LoanFeed:
    master: dict
    instalments: list[FeedInstalment]
    transactions: list[FeedTxn]
    snapshot: dict


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    day = min(d.day, 28)
    return date(d.year + y, m + 1, day)


def emi(principal: Decimal, annual_rate: Decimal, months: int) -> Decimal:
    r = annual_rate / Decimal(1200)
    f = (1 + r) ** months
    return (principal * r * f / (f - 1)).quantize(Q, ROUND_HALF_UP)


def build_schedule(terms: dict) -> list[FeedInstalment]:
    p = Decimal(str(terms["disbursed"]))
    rate = Decimal(str(terms["rate"]))
    n = int(terms["tenure_months"])
    start = date.fromisoformat(terms["repayment_start"])
    e = emi(p, rate, n)
    bal = p
    out = []
    for i in range(1, n + 1):
        interest = (bal * rate / Decimal(1200)).quantize(Q, ROUND_HALF_UP)
        principal = (e - interest) if i < n else bal
        amount = e if i < n else (principal + interest)
        bal -= principal
        out.append(FeedInstalment(i, add_months(start, i - 1), amount.quantize(Q), principal.quantize(Q), interest))
    return out


def _rng(ref: str) -> random.Random:
    return random.Random(int(hashlib.sha256(ref.encode()).hexdigest()[:12], 16))


def _payments(rec: MockBankRecord, insts: list[FeedInstalment], as_of: date) -> list[FeedTxn]:
    rng = _rng(rec.bank_loan_ref)
    ref = rec.bank_loan_ref
    due = [i for i in insts if i.due <= as_of]
    n_due = len(due)
    out: list[FeedTxn] = []
    p = rec.profile
    stop_after = max(1, n_due - rng.randint(2, 5))
    miss = {n_due - 4, n_due - 3} if n_due >= 6 else set()

    def pay(inst, posted, amount, channel="NACH"):
        if posted <= as_of:
            out.append(FeedTxn(f"{ref}-T{inst.no:03d}", posted, posted, amount.quantize(Q), "PAYMENT", channel,
                               f"UTR{rng.randint(10**9, 10**10 - 1)}"))

    for k, inst in enumerate(due, start=1):
        if p in ("PUNCTUAL", "CLOSED"):
            pay(inst, inst.due - timedelta(days=rng.randint(0, 3)), inst.amount)
        elif p == "OCCASIONAL_LATE":
            late = rng.randint(8, 20) if k % 5 == 3 else 0
            pay(inst, inst.due + timedelta(days=late), inst.amount, "UPI" if late else "NACH")
        elif p == "PARTIAL_PAYER":
            pay(inst, inst.due + timedelta(days=rng.randint(0, 5)), inst.amount * Decimal("0.60"), "UPI")
        elif p == "CHRONIC_OVERDUE":
            if k <= stop_after:
                pay(inst, inst.due, inst.amount)
        elif p == "EARLY_OVERDUE":
            if k < n_due:
                pay(inst, inst.due, inst.amount)
        elif p == "RECOVERED":
            if k in miss:
                continue
            if miss and k == max(miss) + 1:
                pay(inst, inst.due + timedelta(days=5), inst.amount * 3, "NEFT")
            else:
                pay(inst, inst.due, inst.amount)
        elif p == "REVERSAL":
            pay(inst, inst.due, inst.amount)
            if k == n_due - 1:
                posted = inst.due + timedelta(days=3)
                if posted <= as_of:
                    out.append(FeedTxn(f"{ref}-R{inst.no:03d}", posted, posted, -inst.amount, "REVERSAL", "NACH",
                                       "NACH_RETURN_INSUFFICIENT_FUNDS", reverses=f"{ref}-T{inst.no:03d}"))
    if rec.terms.get("quirk") == "UNIDENTIFIED_CREDIT" and len(due) > 1:
        posted = due[-2].due + timedelta(days=9)
        if posted <= as_of:
            out.append(FeedTxn(f"{ref}-U001", posted, posted, Decimal("2500.00"), "PAYMENT", "CASH_DEPOSIT", None))
    return sorted(out, key=lambda t: (t.posted, t.ref))


def _allocate(insts: list[FeedInstalment], txns: list[FeedTxn], quirk: str | None) -> None:
    """Bank-side FIFO allocation. DAPRO stores the result; it never computes allocation itself."""
    by_ref: dict[str, FeedTxn] = {}
    for t in txns:
        if t.kind == "PAYMENT":
            if t.ref.endswith("-U001") and quirk == "UNIDENTIFIED_CREDIT":
                t.allocations = []  # bank could not allocate: DAPRO must reconcile, not guess
                continue
            remaining = t.amount
            for inst in insts:
                if remaining <= 0:
                    break
                gap = inst.amount - inst.allocated
                if gap <= 0:
                    continue
                take = min(gap, remaining)
                inst.allocated += take
                remaining -= take
                t.allocations.append({"instalment_no": inst.no, "amount": f"{take:.2f}"})
            by_ref[t.ref] = t
        elif t.kind == "REVERSAL" and t.reverses in by_ref:
            for a in by_ref[t.reverses].allocations:
                inst = insts[a["instalment_no"] - 1]
                inst.allocated -= Decimal(a["amount"])
                t.allocations.append({"instalment_no": a["instalment_no"], "amount": f"-{a['amount']}"})
    for inst in insts:
        inst.bank_status = "PAID" if inst.allocated >= inst.amount else ("PARTIAL" if inst.allocated > 0 else "UNPAID")


class MockBankAdapter:
    mode = "MOCK"
    name = SOURCE

    def __init__(self, db, bank_org_id):
        self.db = db
        self.bank_org_id = bank_org_id

    def lookup(self, bank_loan_ref: str) -> MockBankRecord | None:
        return self.db.execute(select(MockBankRecord).where(MockBankRecord.bank_org_id == self.bank_org_id,
                                                            MockBankRecord.bank_loan_ref == bank_loan_ref)).scalar()

    def all_refs(self) -> list[str]:
        return list(self.db.execute(select(MockBankRecord.bank_loan_ref)
                                    .where(MockBankRecord.bank_org_id == self.bank_org_id)).scalars())

    def fetch(self, rec: MockBankRecord, as_of: date) -> LoanFeed:
        t = rec.terms
        start = date.fromisoformat(t["repayment_start"])
        insts = build_schedule(t) if start <= as_of + timedelta(days=60) else []
        txns = _payments(rec, insts, as_of) if insts else []
        _allocate(insts, txns, t.get("quirk"))
        past = [i for i in insts if i.due <= as_of]
        overdue = sum((i.amount - i.allocated for i in past), Decimal("0.00"))
        oldest = next((i for i in past if i.allocated < i.amount), None)
        bank_dpd = (as_of - oldest.due).days if oldest else 0
        if t.get("quirk") == "DPD_MISMATCH" and bank_dpd:
            bank_dpd += 2
        disbursed = Decimal(str(t["disbursed"]))
        repaid_principal = sum((i.principal * min(Decimal(1), i.allocated / i.amount) for i in insts),
                               Decimal("0.00"))
        all_paid = bool(insts) and all(i.allocated >= i.amount for i in insts)
        status = "CLOSED" if (rec.profile == "CLOSED" and all_paid) else (
            "MORATORIUM" if as_of < start else "IN_REPAYMENT")
        master = {
            "bank_borrower_ref": rec.bank_borrower_ref, "product_name": t.get("product"), "scheme": t.get("scheme"),
            "bank_status": status, "sanctioned_amount": Decimal(str(t["sanctioned"])), "disbursed_amount": disbursed,
            "sanction_date": date.fromisoformat(t["sanction_date"]),
            "first_disbursement_date": date.fromisoformat(t["disbursement_date"]),
            "moratorium_end": date.fromisoformat(t["moratorium_end"]), "repayment_start": start,
            "tenure_months": int(t["tenure_months"]), "interest_rate_pct": Decimal(str(t["rate"])),
            "emi_amount": insts[0].amount if insts else emi(disbursed, Decimal(str(t["rate"])),
                                                            int(t["tenure_months"])),
            "branch_code": rec.branch_code,
        }
        snapshot = {"principal_outstanding": (disbursed - repaid_principal).quantize(Q),
                    "interest_charges": sum((i.interest for i in past if i.allocated < i.amount), Decimal("0.00")),
                    "overdue_amount": overdue.quantize(Q), "total_due": overdue.quantize(Q), "bank_dpd": bank_dpd,
                    "bank_status": status}
        return LoanFeed(master, insts, txns, snapshot)
