"""Seed stage 2: students with contacts, addresses, academic and employment history, consents."""
from datetime import UTC, date, datetime, time, timedelta

from app.common.clock import business_today
from app.common.refs import next_ref
from app.models.students import (
    AcademicRecord,
    AddressVerification,
    Consent,
    ContactPreference,
    DuplicateCandidate,
    EmploymentRecord,
    Student,
    StudentAddress,
    StudentContact,
)
from app.seed.data import (
    CITIES_ABROAD,
    CITIES_IN,
    CITIES_TN,
    EMPLOYERS,
    JOBS,
    PROGRAMMES,
    RNG,
    STREETS,
    mobile,
    norm_name,
    person,
)

TODAY = business_today()
COHORTS = [2019, 2020, 2020, 2021, 2021, 2021, 2022, 2022, 2022, 2023, 2023, 2024, 2025]
GRAD_STATES = ["EMPLOYED"] * 11 + ["SELF_EMPLOYED", "FURTHER_STUDY", "FURTHER_STUDY", "UNEMPLOYED", "UNEMPLOYED",
                                   "GRADUATED", "GRADUATED", "UNKNOWN"]


def _dt(d: date) -> datetime:
    return datetime.combine(d, time(10, 30), tzinfo=UTC)


def _address(db, tid, s, kind, source, verification, created: date, city=None, abroad=None, current=True):
    if abroad:
        c, st, pc, country = abroad
        line1 = f"{RNG.randint(100, 9999)} {RNG.choice(['Oak', 'Maple', 'Cedar', 'Elm'])} Street, Apt {RNG.randint(1, 40)}"
    else:
        c, st, pc = city or RNG.choice(CITIES_TN)
        pc, country = pc + f"{RNG.randint(10, 99)}", "IN"
        line1 = f"No. {RNG.randint(1, 240)}, {RNG.choice(STREETS)}"
    a = StudentAddress(tenant_id=tid, student_id=s.id, kind=kind, line1=line1, line2=None, city=c, state=st,
                       postal_code=pc, country=country, source_type=source, verification=verification,
                       verification_method="DOCUMENT" if verification == "VERIFIED" else None,
                       verified_at=_dt(created) + timedelta(days=5) if verification == "VERIFIED" else None,
                       effective_from=created, is_current=current, created_at=_dt(created))
    db.add(a)
    db.flush()
    return a


def make_student(db, F, college, cohort: int, idx: int, recent: bool = False, name=None, dob=None):
    tid = F["tenant"].id
    first, last, g = person() if name is None else (*name, "M")
    prog, course, dur = RNG.choice(PROGRAMMES)
    start = date(cohort, 7, 15)
    end = date(cohort + dur, 5, 31)
    dob = dob or date(cohort - (18 if dur == 4 else 22) - RNG.randint(0, 1), RNG.randint(1, 12), RNG.randint(1, 28))
    graduated = end < TODAY
    status = RNG.choice(GRAD_STATES) if graduated else "STUDYING"
    created = (TODAY - timedelta(days=RNG.randint(1, 12))) if recent else start - timedelta(days=RNG.randint(0, 10))
    full = f"{first} {last}"
    s = Student(tenant_id=tid, dapro_ref=next_ref(db, tid, "student", "DAP"), college_org_id=college.id,
                campus_unit_id=F["units"][f"{college.code}-MAIN"].id,
                college_student_id=f"{college.code}{cohort % 100:02d}{prog[0]}{idx:04d}", first_name=first,
                last_name=last, full_name=full, name_norm=norm_name(full), dob=None if recent and idx % 2 else dob,
                gender=g, kyc_ref_last4=None if recent else f"{RNG.randint(1000, 9999)}", nationality="IN",
                lifecycle_status=status, verification_status="UNVERIFIED" if recent else "VERIFIED",
                source="COLLEGE_IMPORT", source_ref=f"{college.code}-SIS-BATCH-{cohort}", data_origin="DEMO",
                created_by=F["users"]["priya"].id if college.code == "NBIT" else F["users"]["rce_admin"].id,
                created_at=_dt(created))
    db.add(s)
    db.flush()
    email = f"{first.lower()}.{last.lower()}{idx % 97}@mail.demo"
    mob = mobile()
    s.primary_email = email
    db.add(StudentContact(tenant_id=tid, student_id=s.id, kind="EMAIL", value=email, is_primary=True,
                          source="COLLEGE_PROVIDED", verification="VERIFIED", effective_from=created))
    if not recent:
        s.primary_mobile = mob
        db.add(StudentContact(tenant_id=tid, student_id=s.id, kind="MOBILE", value=mob, is_primary=True,
                              source="COLLEGE_PROVIDED", verification="VERIFIED", effective_from=created))
        _address(db, tid, s, "PERMANENT", "COLLEGE_PROVIDED", "VERIFIED", created)
    rec = AcademicRecord(tenant_id=tid, student_id=s.id, college_org_id=college.id, programme=prog, course=course,
                         cohort_year=cohort, start_date=start, expected_completion=end,
                         actual_completion=end if graduated else None,
                         enrolment_status="COMPLETED" if graduated else "ENROLLED", source="COLLEGE_PROVIDED",
                         verification="VERIFIED", created_at=_dt(created))
    db.add(rec)
    return s, rec, graduated


def post_study(db, F, s: Student, rec: AcademicRecord):
    """Current address, verification state and employment history for graduates (FR-ADR, FR-EMP)."""
    tid = F["tenant"].id
    end = rec.expected_completion
    roll = RNG.random()
    abroad = RNG.choice(CITIES_ABROAD) if s.lifecycle_status in ("EMPLOYED", "FURTHER_STUDY") and roll < 0.14 else None
    if RNG.random() < 0.3:  # an older current address superseded later: history (FR-ADR-03)
        old = _address(db, tid, s, "CURRENT", "BORROWER_REPORTED", "VERIFIED", end + timedelta(days=40),
                       RNG.choice(CITIES_TN), current=False)
        old.superseded_at = _dt(end + timedelta(days=300))
    if RNG.random() < 0.82:
        v = RNG.choices(["VERIFIED", "PENDING", "UNVERIFIED", "FAILED", "DISPUTED"], [50, 22, 10, 10, 8])[0]
        created = end + timedelta(days=RNG.randint(60, 420))
        if created > TODAY:
            created = TODAY - timedelta(days=RNG.randint(5, 30))
        a = _address(db, tid, s, "CURRENT", "BORROWER_REPORTED", v, created,
                     None if abroad else RNG.choice(CITIES_TN + CITIES_IN), abroad)
        if v in ("PENDING", "FAILED"):
            db.add(AddressVerification(
                tenant_id=tid, address_id=a.id, student_id=s.id, method=RNG.choice(["DOCUMENT", "POSTAL", "FIELD_VISIT"]),
                status=v, requested_by=F["users"]["ravi"].id,
                outcome_notes="Addressee not known at this address (postal return)" if v == "FAILED" else None,
                performed_by=F["users"]["ravi"].id if v == "FAILED" else None,
                performed_at=_dt(created + timedelta(days=12)) if v == "FAILED" else None, created_at=_dt(created)))
        if v in ("FAILED", "DISPUTED"):
            a.verification_method = "POSTAL" if v == "FAILED" else None
            a.notes = "Borrower states this address is outdated" if v == "DISPUTED" else None
    st = s.lifecycle_status
    if st in ("EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "FURTHER_STUDY"):
        rep = end + timedelta(days=RNG.randint(30, 200))
        if rep > TODAY:
            rep = TODAY - timedelta(days=3)
        if st == "EMPLOYED" and RNG.random() < 0.3:
            e0, sec0 = RNG.choice(EMPLOYERS)
            first = EmploymentRecord(tenant_id=s.tenant_id, student_id=s.id, status="EMPLOYED", employer_name=e0,
                                     job_title=RNG.choice(JOBS), sector=sec0, city="Chennai", country="IN",
                                     source="BORROWER_REPORTED", verification="UNVERIFIED", reported_on=rep,
                                     effective_from=rep, is_current=False, superseded_at=_dt(rep + timedelta(days=240)),
                                     created_at=_dt(rep))
            db.add(first)
            rep = rep + timedelta(days=240) if rep + timedelta(days=240) < TODAY else rep
        emp, sec = RNG.choice(EMPLOYERS)
        verified = RNG.random() < 0.4
        db.add(EmploymentRecord(
            tenant_id=s.tenant_id, student_id=s.id, status=st,
            employer_name=emp if st in ("EMPLOYED", "SELF_EMPLOYED") else None,
            job_title=RNG.choice(JOBS) if st == "EMPLOYED" else ("Founder" if st == "SELF_EMPLOYED" else None),
            sector=sec if st in ("EMPLOYED", "SELF_EMPLOYED") else None,
            city=abroad[0] if abroad else RNG.choice(CITIES_TN + CITIES_IN)[0], country=abroad[3] if abroad else "IN",
            source="INSTITUTION_VERIFIED" if verified else "BORROWER_REPORTED",
            verification="VERIFIED" if verified else "UNVERIFIED", reported_on=rep, effective_from=rep,
            notes="Pursuing postgraduate study" if st == "FURTHER_STUDY" else None, created_at=_dt(rep)))


def consents(db, s: Student, withdrawn: bool):
    base = s.created_at
    db.add(Consent(tenant_id=s.tenant_id, student_id=s.id, basis="CONTRACT", purposes=["MONITORING", "FOLLOW_UP"],
                   notice_version="PN-2024.1", source="LOAN_AGREEMENT", valid_from=base))
    db.add(Consent(tenant_id=s.tenant_id, student_id=s.id, basis="CONSENT", purposes=["ENGAGEMENT"],
                   notice_version="PN-2024.1", source="COLLEGE_ONBOARDING_FORM", valid_from=base,
                   withdrawn_at=datetime.now(UTC) - timedelta(days=20) if withdrawn else None))
    db.add(ContactPreference(tenant_id=s.tenant_id, student_id=s.id, channel="EMAIL", allowed=True))
    db.add(ContactPreference(tenant_id=s.tenant_id, student_id=s.id, channel="SMS", allowed=RNG.random() < 0.85))


def seed_students(db, F) -> list[dict]:
    out = []
    plan = [(F["orgs"]["NBIT"], 92), (F["orgs"]["RCE"], 68)]
    for college, count in plan:
        for i in range(count):
            cohort = RNG.choice(COHORTS)
            s, rec, graduated = make_student(db, F, college, cohort, i + 1)
            if graduated:
                post_study(db, F, s, rec)
            if i in (7, 31) and graduated:
                rec.enrolment_status, rec.actual_completion = "DISCONTINUED", None
                s.lifecycle_status = "UNKNOWN"
            out.append({"student": s, "academic": rec, "graduated": graduated, "college": college})
        for j in range(4):  # recently added, incomplete profiles (dashboard: missing information)
            s, rec, _ = make_student(db, F, college, 2026, 900 + j, recent=True)
            out.append({"student": s, "academic": rec, "graduated": False, "college": college, "recent": True})
    # possible duplicate pair (FR-STU-04)
    a = out[3]["student"]
    dup, rec, _ = make_student(db, F, a.college_org_id == F["orgs"]["NBIT"].id and F["orgs"]["NBIT"] or F["orgs"]["RCE"],
                               out[3]["academic"].cohort_year, 950, name=(a.first_name, a.last_name), dob=a.dob)
    db.flush()
    db.add(DuplicateCandidate(tenant_id=a.tenant_id, student_id=dup.id, candidate_student_id=a.id,
                              match_fields=["full_name", "dob"], score=92, status="OPEN"))
    out.append({"student": dup, "academic": rec, "graduated": False, "college": None, "duplicate": True})
    db.flush()
    return out
