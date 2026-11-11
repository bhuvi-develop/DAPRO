"""Seed stage 1: tenants, organizations, units, agreements, roles, users, policy, integrations, templates, rules."""
from datetime import UTC, date, datetime, timedelta

from app.common.policy import DEFAULTS
from app.core.config import get_settings
from app.core.permissions import ROLE_MATRIX
from app.core.security import hash_password
from app.models.engagement import NotificationTemplate
from app.models.iam import Organization, OrgUnit, Role, SharingAgreement, Tenant, User, UserRole
from app.models.loans import Integration
from app.models.ops import RiskRule
from app.models.platform import PolicyConfig
from app.modules.risk.catalog import RULES

POLICY_DESCRIPTIONS = {
    "DPD_BUCKETS": "Illustrative DPD buckets (RD 10.2). Not regulatory or NPA classifications.",
    "REPAYMENT_RULES": "Grace period and partial-payment treatment. Allocation is always bank-supplied (BR-04).",
    "DATA_FRESHNESS": "Hours after which a bank snapshot is shown as STALE (BR-03).",
    "GRIEVANCE_SLA": "Days to resolve a grievance (OD-18 pending).",
    "COMMUNICATION_WINDOW": "Quiet hours and weekly frequency cap for borrower contact (OD-16 pending).",
    "CASE_DEFAULTS": "Default case due dates by priority.",
    "MAKER_CHECKER": "Second-user approval switches (RD 6.1).",
}

TEMPLATES = [
    ("EMI_REMINDER", "Upcoming EMI reminder", "EMAIL", "REMINDER", "Your education loan instalment is due soon",
     "Dear {name}, this is a reminder from {bank} that your instalment of INR {amount} is due on {due_date}. "
     "If you have already paid, please ignore this message. This message does not confirm any payment."),
    ("EMI_REMINDER_SMS", "Upcoming EMI reminder (SMS)", "SMS", "REMINDER", None,
     "{bank}: EMI of INR {amount} due {due_date}. Ignore if paid. Queries: reply via DAPRO portal."),
    ("CONTACT_UPDATE_REQUEST", "Contact details update request", "EMAIL", "UPDATE_REQUEST",
     "Please confirm your contact details",
     "Dear {name}, please confirm your current address and phone number through the DAPRO borrower portal."),
    ("POST_STUDY_UPDATE", "Post-study status update request", "EMAIL", "UPDATE_REQUEST",
     "Tell us how you are doing after graduation",
     "Dear {name}, congratulations on completing your course. You may voluntarily share your current status."),
    ("GRIEVANCE_ACK", "Grievance acknowledgement", "EMAIL", "GRIEVANCE_ACK", "We received your request {ref}",
     "Dear {name}, we have received your request {ref}. We will respond by {due_date}."),
    ("GUARANTOR_NOTICE", "Guarantor information notice", "EMAIL", "GUARANTOR_NOTICE",
     "Information about a loan you guaranteed",
     "Dear {name}, as guarantor under agreement {agreement_ref}, the bank is informing you of the loan status."),
]


def seed_policies(db, tenant_id, label: str = "DEMO_FIXTURE"):
    for key, value in DEFAULTS.items():
        db.add(PolicyConfig(tenant_id=tenant_id, key=key, version=1, value=value, status="ACTIVE",
                            approval_label=label, description=POLICY_DESCRIPTIONS[key],
                            effective_from=date(2024, 1, 1)))


def seed_roles(db, tenant_id) -> dict[str, Role]:
    roles = {}
    for code, spec in ROLE_MATRIX.items():
        r = Role(tenant_id=tenant_id, code=code, name=spec["name"], description=spec["description"],
                 org_types=spec["org_types"], permissions=spec["permissions"], is_system=True)
        db.add(r)
        roles[code] = r
    db.flush()
    return roles


def add_user(db, tenant_id, org, roles, role_code, email, name, title, unit=None, student_id=None, status="ACTIVE"):
    pw = get_settings().demo_password
    u = User(tenant_id=tenant_id, org_id=org.id, org_unit_id=unit.id if unit else None, email=email, full_name=name,
             title=title, password_hash=hash_password(pw) if status == "ACTIVE" else None, status=status,
             student_id=student_id, activated_at=datetime.now(UTC) - timedelta(days=200) if status == "ACTIVE" else None)
    db.add(u)
    db.flush()
    db.add(UserRole(user_id=u.id, role_id=roles[role_code].id))
    return u


def org(db, tenant_id, type_, code, name, city, email):
    o = Organization(tenant_id=tenant_id, type=type_, code=code, name=name, legal_name=f"{name} (fictional demo entity)",
                     city=city, state="Tamil Nadu", contact_email=email)
    db.add(o)
    db.flush()
    return o


def unit(db, tenant_id, org_, kind, code, name, city, parent=None):
    u = OrgUnit(tenant_id=tenant_id, org_id=org_.id, kind=kind, code=code, name=name, city=city, state="Tamil Nadu",
                parent_id=parent.id if parent else None)
    db.add(u)
    db.flush()
    return u


def seed_rules_templates(db, tenant_id, approver_id, author_id):
    for r in RULES:
        db.add(RiskRule(tenant_id=tenant_id, code=r["code"], version=1, name=r["name"], category=r["category"],
                        description=r["description"], params=r["params"], severity=r["severity"],
                        recommended_action=r["recommended_action"], status="ACTIVE", approval_label="DEMO_FIXTURE",
                        effective_from=date(2024, 1, 1), created_by=author_id, approved_by=approver_id,
                        approved_at=datetime.now(UTC) - timedelta(days=120), change_reason="Initial demo catalogue"))
    for code, name, channel, purpose, subject, body in TEMPLATES:
        db.add(NotificationTemplate(tenant_id=tenant_id, code=code, version=1, name=name, channel=channel,
                                    purpose=purpose, subject=subject, body=body, status="APPROVED",
                                    approval_label="DEMO_FIXTURE", created_by=author_id, approved_by=approver_id,
                                    approved_at=datetime.now(UTC) - timedelta(days=90)))


def seed_demo_foundation(db, existing=None) -> dict:
    t = existing or Tenant(code="DEMO", name="DAPRO Demo Programme - Education Loan Monitoring Pilot",
                           environment_label="DEMO")
    db.add(t)
    db.flush()
    tid = t.id
    db.info["tenant_id"] = str(tid)
    seed_policies(db, tid)
    roles = seed_roles(db, tid)
    plat = org(db, tid, "PLATFORM", "PLATFORM", "DAPRO Platform Operations", "Chennai", "ops@dapro.demo")
    nbit = org(db, tid, "COLLEGE", "NBIT", "Northbridge Institute of Technology", "Chennai", "registrar@nbit.demo")
    rce = org(db, tid, "COLLEGE", "RCE", "Riverside College of Engineering", "Coimbatore", "office@rce.demo")
    anb = org(db, tid, "BANK", "ANB", "Aurum National Bank", "Chennai", "edu.loans@anb.demo")
    mfb = org(db, tid, "BANK", "MFB", "Meridian Finance Bank", "Coimbatore", "studentloans@mfb.demo")

    units = {
        "NBIT-MAIN": unit(db, tid, nbit, "CAMPUS", "NBIT-MAIN", "NBIT Main Campus, Guindy", "Chennai"),
        "RCE-MAIN": unit(db, tid, rce, "CAMPUS", "RCE-MAIN", "RCE Main Campus, Peelamedu", "Coimbatore"),
    }
    chn = unit(db, tid, anb, "REGION", "ANB-CHN", "ANB Chennai Region", "Chennai")
    cbe = unit(db, tid, anb, "REGION", "ANB-CBE", "ANB Coimbatore Region", "Coimbatore")
    units["ANB-CHN"], units["ANB-CBE"] = chn, cbe
    units["ANB-ANN"] = unit(db, tid, anb, "BRANCH", "ANB-ANN", "ANB Anna Nagar Branch", "Chennai", chn)
    units["ANB-TNG"] = unit(db, tid, anb, "BRANCH", "ANB-TNG", "ANB T. Nagar Branch", "Chennai", chn)
    units["ANB-RSP"] = unit(db, tid, anb, "BRANCH", "ANB-RSP", "ANB R.S. Puram Branch", "Coimbatore", cbe)
    units["MFB-CHC"] = unit(db, tid, mfb, "BRANCH", "MFB-CHC", "MFB Chennai Central Branch", "Chennai")
    units["MFB-CBE"] = unit(db, tid, mfb, "BRANCH", "MFB-CBE", "MFB Coimbatore Branch", "Coimbatore")
    units["ANB-COLL"] = unit(db, tid, anb, "TEAM", "ANB-COLL", "ANB Collections Team", "Chennai")

    for c in (nbit, rce):
        for b in (anb, mfb):
            db.add(SharingAgreement(
                tenant_id=tid, reference=f"DSA-{c.code}-{b.code}-2024", college_org_id=c.id, bank_org_id=b.id,
                purposes=["MONITORING", "ENGAGEMENT", "FOLLOW_UP"],
                shared_fields=["identity", "academic_status", "contact", "loan_linkage", "repayment_status"],
                status="ACTIVE", effective_from=date(2024, 1, 1), approval_label="DEMO_FIXTURE",
                notes="Demo data-sharing agreement. Real agreements require legal approval (NFR-PRV-01, OD-01)."))

    u = {}
    u["platform"] = add_user(db, tid, plat, roles, "PLATFORM_ADMIN", "platform.admin@dapro.demo", "Anand Iyer", "Platform Administrator")
    u["priya"] = add_user(db, tid, nbit, roles, "COLLEGE_ADMIN", "priya.admin@nbit.demo", "Priya Raman", "Registrar - Student Records")
    u["nbit_officer"] = add_user(db, tid, nbit, roles, "COLLEGE_OFFICER", "officer@nbit.demo", "Lavanya Selvam", "Student Services Officer")
    u["rce_admin"] = add_user(db, tid, rce, roles, "COLLEGE_ADMIN", "admin@rce.demo", "Gopal Natarajan", "Student Records Lead")
    u["anb_admin"] = add_user(db, tid, anb, roles, "BANK_ADMIN", "admin@anb.demo", "Rekha Menon", "Bank Administrator")
    u["ravi"] = add_user(db, tid, anb, roles, "BANK_LOAN_OPS", "ravi.ops@anb.demo", "Ravi Subramanian", "Education Loan Operations")
    u["investigator"] = add_user(db, tid, anb, roles, "INVESTIGATION_OFFICER", "investigator@anb.demo", "Deepa Raghavan", "Investigation Officer", units["ANB-COLL"])
    u["meena"] = add_user(db, tid, anb, roles, "COLLECTIONS_MANAGER", "meena.manager@anb.demo", "Meena Krishnan", "Follow-up Manager - Chennai", chn)
    u["anb_manager_all"] = add_user(db, tid, anb, roles, "COLLECTIONS_MANAGER", "head.followup@anb.demo", "Suresh Pillai", "Head - Follow-up Operations")
    u["karthik"] = add_user(db, tid, anb, roles, "FIELD_OFFICER", "karthik.field@anb.demo", "Karthik Murugan", "Field Officer", units["ANB-COLL"])
    u["field2"] = add_user(db, tid, anb, roles, "FIELD_OFFICER", "nithya.field@anb.demo", "Nithya Ganesan", "Field Officer", units["ANB-COLL"])
    u["sanjay"] = add_user(db, tid, anb, roles, "AUDITOR", "sanjay.audit@anb.demo", "Sanjay Chandran", "Compliance Reviewer")
    u["mfb_ops"] = add_user(db, tid, mfb, roles, "BANK_LOAN_OPS", "ops@mfb.demo", "Harish Venkatesan", "Loan Operations")
    u["mfb_admin"] = add_user(db, tid, mfb, roles, "BANK_ADMIN", "admin@mfb.demo", "Kalpana Rao", "Bank Administrator")
    u["mfb_manager"] = add_user(db, tid, mfb, roles, "COLLECTIONS_MANAGER", "manager@mfb.demo", "Vikram Shankar", "Follow-up Manager")
    u["invited"] = add_user(db, tid, anb, roles, "INVESTIGATION_OFFICER", "new.investigator@anb.demo", "Rahul Prakash", "Investigation Officer (invited)", status="INVITED")

    now = datetime.now(UTC)
    for o, kind, name, provider, mode, health, extra in [
        (anb, "BANK_LOAN_FEED", "ANB loan and repayment feed", "MOCK_BANK_FEED", "MOCK", "HEALTHY", {}),
        (mfb, "BANK_LOAN_FEED", "MFB loan and repayment feed", "MOCK_BANK_FEED", "MOCK", "HEALTHY", {}),
        (nbit, "COLLEGE_SIS", "NBIT student information system", "CSV_IMPORT", "MOCK", "HEALTHY", {"format": "DAPRO CSV v1"}),
        (rce, "COLLEGE_SIS", "RCE ERP integration", "NONE", "NOT_CONFIGURED", "UNKNOWN", {}),
        (None, "EMAIL", "Transactional email", "MOCK_EMAIL", "MOCK", "HEALTHY", {"note": "Messages are recorded, not delivered"}),
        (None, "SMS", "SMS gateway (DLT registration pending)", "MOCK_SMS", "MOCK", "HEALTHY", {"note": "OD-16"}),
        (None, "OBJECT_STORAGE", "Evidence storage", "LOCAL_VOLUME", "LIVE", "HEALTHY", {}),
    ]:
        db.add(Integration(tenant_id=tid, org_id=o.id if o else None, kind=kind, name=name, provider=provider,
                           mode=mode, health=health, last_success_at=now if health == "HEALTHY" else None,
                           refresh_interval_hours=24, config=extra))
    seed_rules_templates(db, tid, u["ravi"].id, u["meena"].id)
    db.flush()
    return {"tenant": t, "orgs": {"PLATFORM": plat, "NBIT": nbit, "RCE": rce, "ANB": anb, "MFB": mfb},
            "units": units, "users": u, "roles": roles}


def seed_isolation_tenant(db) -> dict:
    """A second tenant used to prove cross-tenant isolation (AC-01, NFR-SEC-03)."""
    t = Tenant(code="ISOTEST", name="Isolation Test Programme", environment_label="DEMO")
    db.add(t)
    db.flush()
    db.info["tenant_id"] = str(t.id)
    seed_policies(db, t.id)
    roles = seed_roles(db, t.id)
    col = org(db, t.id, "COLLEGE", "ISOCOL", "Isolation Test College", "Madurai", "x@iso.demo")
    bank = org(db, t.id, "BANK", "ISOBANK", "Isolation Test Bank", "Madurai", "y@iso.demo")
    users = {"college": add_user(db, t.id, col, roles, "COLLEGE_ADMIN", "admin@isocollege.demo", "Iso College Admin", "Admin"),
             "bank": add_user(db, t.id, bank, roles, "BANK_LOAN_OPS", "ops@isobank.demo", "Iso Bank Ops", "Ops")}
    from app.models.loans import LoanAccount
    from app.models.students import Student
    for i, (first, last) in enumerate([("Isolation", "Student One"), ("Isolation", "Student Two"),
                                       ("Isolation", "Student Three")], start=1):
        s = Student(tenant_id=t.id, dapro_ref=f"ISO-2026-{i:06d}", college_org_id=col.id, college_student_id=f"ISO{i:03d}",
                    first_name=first, last_name=last, full_name=f"{first} {last}", name_norm=f"{first} {last}".upper(),
                    lifecycle_status="EMPLOYED", data_origin="DEMO", primary_email=f"iso{i}@mail.demo")
        db.add(s)
        db.flush()
        db.add(LoanAccount(tenant_id=t.id, bank_org_id=bank.id, student_id=s.id, college_org_id=col.id,
                           bank_loan_ref=f"ISO-LOAN-{i:04d}", link_status="LINKED", data_origin="DEMO",
                           sync_state="CURRENT", repayment_status="OVERDUE", dpd=45, dpd_bucket="DPD_31_60"))
    return {"tenant": t, "college": col, "bank": bank, "users": users}
