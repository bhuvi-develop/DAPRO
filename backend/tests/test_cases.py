"""Case workspace: scope, state machine, evidence-before-escalation, bank-confirmed closure (FR-CAS, FR-FLD-07, AC-12)."""
from sqlalchemy import text

from tests.ops_helpers import anb_student_with_loan, uid


def _new_case(client, h, owner_db, offset=0):
    sid, lid = anb_student_with_loan(owner_db, "OVERDUE", offset)
    r = client.post("/api/v1/cases", headers=h, json={"student_id": str(sid), "loan_id": str(lid),
                                                      "category": "REPAYMENT_FOLLOW_UP", "priority": "HIGH",
                                                      "reason": "Test follow-up for bank-confirmed overdue"})
    assert r.status_code == 201, r.text
    return r.json(), lid


def test_list_has_display_names_and_open_filter(client, auth):
    page = client.get("/api/v1/cases?status=open&size=50", headers=auth("manager_all")).json()
    assert page["total"] > 0
    item = page["items"][0]
    assert item["student_name"] and item["dapro_ref"] and "owner_name" in item
    assert all(i["status"] not in ("RESOLVED", "CLOSED") for i in page["items"])


def test_field_officer_sees_only_assigned_cases(client, auth, owner_db):
    karthik = uid(owner_db, "karthik.field@anb.demo")
    page = client.get("/api/v1/cases?size=100", headers=auth("field")).json()
    assert page["total"] > 0 and all(i["owner_id"] == karthik for i in page["items"])
    other = owner_db.execute(text("select id from cases where owner_id is distinct from :k limit 1"),
                             {"k": karthik}).scalar()
    assert client.get(f"/api/v1/cases/{other}", headers=auth("field")).status_code == 404


def test_college_and_other_bank_cannot_read_anb_cases(client, auth, owner_db):
    assert client.get("/api/v1/cases", headers=auth("college_admin")).status_code == 403
    anb_case = owner_db.execute(text("select c.id from cases c join organizations o on o.id = c.bank_org_id "
                                     "where o.code = :b limit 1"), {"b": "ANB"}).scalar()
    assert client.get(f"/api/v1/cases/{anb_case}", headers=auth("mfb_manager")).status_code == 404


def test_case_lifecycle_guards(client, auth, owner_db):
    h = auth("manager_all")
    case, lid = _new_case(client, h, owner_db, 0)
    cid = case["id"]
    inv = uid(owner_db, "investigator@anb.demo")
    bad = client.post(f"/api/v1/cases/{cid}/assign", headers=h, json={"owner_id": uid(owner_db, "ops@mfb.demo")})
    assert bad.status_code == 400
    c = client.post(f"/api/v1/cases/{cid}/assign", headers=h, json={"owner_id": inv}).json()
    assert c["status"] == "ASSIGNED"
    t = {x["to"]: x for x in c["allowed_transitions"]}
    assert t["ESCALATED"]["permitted"] is False and t["ESCALATED"]["reason_if_blocked"]
    assert set(t["ESCALATED"]) >= {"to", "label", "requires", "permitted", "reason_if_blocked"}
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=h, json={"to": "CLOSED", "note": "x"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION" and r.json()["error"]["next_step"]
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=h, json={"to": "ESCALATED", "note": "Escalating now"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "EVIDENCE_REQUIRED"
    f = client.post(f"/api/v1/cases/{cid}/follow-ups", headers=auth("investigator"),
                    json={"channel": "PHONE", "outcome": "NO_ANSWER", "notes": "No answer on registered mobile"})
    assert f.status_code == 201 and f.json()["status"] == "CONTACT_ATTEMPTED"
    cm = client.post(f"/api/v1/cases/{cid}/commitments", headers=auth("investigator"),
                     json={"amount": "5000.00", "promised_date": "2099-01-10"})
    assert cm.status_code == 201 and cm.json()["is_payment"] is False
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=h,
                    json={"to": "RESOLVED", "note": "Borrower promised", "resolution_type": "PAYMENT_CONFIRMED",
                          "bank_txn_ref": "NOT-A-BANK-TXN"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "BANK_CONFIRMATION_REQUIRED"
    txn = owner_db.execute(text("select bank_txn_ref from repayment_transactions where loan_id = :l and kind = :k "
                                "limit 1"), {"l": lid, "k": "PAYMENT"}).scalar()
    assert client.post(f"/api/v1/cases/{cid}/transition", headers=auth("investigator"),
                       json={"to": "RESOLVED", "note": "n", "resolution_type": "DATA_CORRECTED"}).status_code == 403
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=h,
                    json={"to": "RESOLVED", "note": "Bank feed shows payment", "resolution_type": "PAYMENT_CONFIRMED",
                          "bank_txn_ref": txn})
    assert r.status_code == 200 and r.json()["resolution_evidence"]["bank_txn_ref"] == txn
    client.post(f"/api/v1/cases/{cid}/assign", headers=h, json={"owner_id": uid(owner_db, "head.followup@anb.demo")})
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=h, json={"to": "CLOSED", "note": "Closing my own"})
    assert r.status_code in (409,) and r.json()["error"]["code"] in ("SOD_CONFLICT", "INVALID_TRANSITION")
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=auth("loan_ops"), json={"to": "CLOSED", "note": "Verified"})
    assert r.status_code == 200 and r.json()["status"] == "CLOSED"
    assert any(e["type"] == "STATUS_CHANGED" for e in r.json()["timeline"])


def test_escalation_after_follow_up_and_version_check(client, auth, owner_db):
    h = auth("manager_all")
    case, _ = _new_case(client, h, owner_db, 1)
    cid = case["id"]
    client.post(f"/api/v1/cases/{cid}/assign", headers=h, json={"owner_id": uid(owner_db, "investigator@anb.demo")})
    client.post(f"/api/v1/cases/{cid}/follow-ups", headers=h,
                json={"channel": "PHONE", "outcome": "NO_ANSWER", "notes": "Second attempt no answer"})
    r = client.post(f"/api/v1/cases/{cid}/transition", headers=h, json={"to": "ESCALATED", "note": "Manager review"})
    assert r.status_code == 200 and r.json()["status"] == "ESCALATED"
    stale = client.patch(f"/api/v1/cases/{cid}", headers={**h, "If-Match": "1"}, json={"priority": "LOW"})
    assert stale.status_code == 412


def test_evidence_upload_validates_type(client, auth, owner_db):
    h = auth("manager_all")
    cid = client.get("/api/v1/cases?status=open", headers=h).json()["items"][0]["id"]
    bad = client.post(f"/api/v1/cases/{cid}/evidence", headers=h, data={"title": "Script"},
                      files={"file": ("x.pdf", b"<script>alert(1)</script>", "application/pdf")})
    assert bad.status_code == 400
    ok = client.post(f"/api/v1/cases/{cid}/evidence", headers=h, data={"title": "Bank letter"},
                     files={"file": ("letter.pdf", b"%PDF-1.4 demo", "application/pdf")})
    assert ok.status_code == 201 and len(ok.json()["sha256"]) == 64
    dl = client.get(f"/api/v1/evidence/{ok.json()['id']}/download", headers=h)
    assert dl.status_code == 200 and dl.content.startswith(b"%PDF")
