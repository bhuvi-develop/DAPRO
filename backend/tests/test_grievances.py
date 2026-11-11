"""Grievances and corrections (FR-GRV-01..03, BR-14, AC-13, US-05)."""
from sqlalchemy import text

from tests.conftest import login
from tests.ops_helpers import anb_student_with_loan, borrowers, uid


def test_conflict_of_interest_blocks_assignment(client, auth, owner_db):
    sid, _ = anb_student_with_loan(owner_db, "OVERDUE", 2)
    karthik = uid(owner_db, "karthik.field@anb.demo")
    g = client.post("/api/v1/grievances", headers=auth("manager_all"),
                    json={"student_id": str(sid), "category": "CONDUCT_COMPLAINT", "subject": "Visit conduct",
                          "description": "Family reports the visit was at an unsuitable hour.",
                          "subject_user_id": karthik}).json()
    assert g["ref"].startswith("GRV-") and g["due_on"]
    r = client.post(f"/api/v1/grievances/{g['id']}/assign", headers=auth("manager_all"), json={"owner_id": karthik})
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONFLICT_OF_INTEREST"
    ok = client.post(f"/api/v1/grievances/{g['id']}/assign", headers=auth("manager_all"),
                     json={"owner_id": uid(owner_db, "head.followup@anb.demo")})
    assert ok.status_code == 200 and ok.json()["owner_name"]


def test_dispute_pauses_case_and_resolution_restores_it(client, auth):
    case = client.get("/api/v1/cases?status=CONTACT_ATTEMPTED", headers=auth("manager_all")).json()["items"][0]
    g = client.post("/api/v1/grievances", headers=auth("loan_ops"),
                    json={"student_id": case["student"]["id"], "loan_id": case["loan"]["id"],
                          "category": "AMOUNT_DISPUTE", "subject": "Amount already paid",
                          "description": "Borrower says the EMI was paid by UPI."}).json()
    assert g["case_id"] == case["id"]
    assert client.get(f"/api/v1/cases/{case['id']}", headers=auth("manager_all")).json()["status"] == "DISPUTED"
    h = auth("loan_ops")
    bad = client.post(f"/api/v1/grievances/{g['id']}/transition", headers=h, json={"to": "RESOLVED", "reason": "ok ok"})
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "INVALID_TRANSITION"
    client.post(f"/api/v1/grievances/{g['id']}/transition", headers=h, json={"to": "UNDER_REVIEW"})
    assert client.post(f"/api/v1/grievances/{g['id']}/transition", headers=h, json={"to": "REJECTED"}).status_code == 400
    r = client.post(f"/api/v1/grievances/{g['id']}/transition", headers=h,
                    json={"to": "RESOLVED", "reason": "Bank confirmed the payment; record corrected at source."})
    assert r.status_code == 200
    assert client.get(f"/api/v1/cases/{case['id']}", headers=auth("manager_all")).json()["status"] == "CONTACT_ATTEMPTED"


def test_data_correction_preserves_history(client, owner_db):
    """AC-13 end to end + BR-14: borrower raises, staff resolves, old value retained."""
    email, sid = borrowers(owner_db)[0]
    b = login(client, email)
    old = owner_db.execute(text("select primary_email from students where id = :s"), {"s": sid}).scalar()
    g = client.post("/api/v1/portal/grievances", headers=b,
                    json={"category": "DATA_CORRECTION", "subject": "New email address",
                          "description": "Please use my new email address.", "correction_field": "primary_email",
                          "correction_requested_value": "fresh.address@mail.demo"})
    assert g.status_code == 201, g.text
    gid = g.json()["id"]
    college = owner_db.execute(text("select o.code from students s join organizations o on o.id = s.college_org_id "
                                    "where s.id = :s"), {"s": sid}).scalar()
    staff = login(client, "priya.admin@nbit.demo" if college == "NBIT" else "admin@rce.demo")
    client.post(f"/api/v1/grievances/{gid}/transition", headers=staff, json={"to": "UNDER_REVIEW"})
    client.post(f"/api/v1/grievances/{gid}/respond", headers=staff,
                json={"message": "Internal: verified by phone", "visibility": "INTERNAL"})
    r = client.post(f"/api/v1/grievances/{gid}/transition", headers=staff,
                    json={"to": "RESOLVED", "reason": "Verified and updated.", "approve_correction": True})
    assert r.status_code == 200, r.text
    owner_db.expire_all()
    new = owner_db.execute(text("select primary_email from students where id = :s"), {"s": sid}).scalar()
    assert new == "fresh.address@mail.demo"
    hist = owner_db.execute(text("select old_value, approved_by from student_field_changes where student_id = :s "
                                 "and field = :f order by created_at desc limit 1"),
                            {"s": sid, "f": "primary_email"}).one()
    assert hist.old_value == old and hist.approved_by is not None
    seen = client.get(f"/api/v1/portal/grievances/{gid}", headers=b).json()
    assert seen["status"] == "RESOLVED" and all(e["visibility"] == "BORROWER" for e in seen["events"])


def test_grievance_inputs_are_constrained(client, auth, owner_db):
    """Free-form channel/priority/visibility/transition values are rejected at the API boundary."""
    sid, _ = anb_student_with_loan(owner_db, "OVERDUE", 2)
    h = auth("manager_all")
    base = {"student_id": str(sid), "category": "OTHER", "subject": "General query",
            "description": "Borrower asked for a statement copy."}
    for bad in ({"channel": "WHATSAPP_SCRAPE"}, {"priority": "URGENT!!"}):
        r = client.post("/api/v1/grievances", headers=h, json={**base, **bad})
        assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_FAILED"
    g = client.post("/api/v1/grievances", headers=h, json={**base, "channel": "PHONE", "priority": "HIGH"}).json()
    assert g["channel"] == "PHONE" and g["priority"] == "HIGH"
    r = client.post(f"/api/v1/grievances/{g['id']}/respond", headers=h, json={"message": "Noted", "visibility": "PUBLIC"})
    assert r.status_code == 400
    r = client.post(f"/api/v1/grievances/{g['id']}/transition", headers=h, json={"to": "SUBMITTED"})
    assert r.status_code == 400
