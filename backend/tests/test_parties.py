"""Guarantor maker-checker and witness separation (FR-GUA, BR-07, AC-09)."""
import os
import uuid

from sqlalchemy import text

PW = "Approver@2026x"


def _anb_loan_with_guarantor(db):
    return db.execute(text("select l.id, g.id gid from loan_accounts l join guarantors g on g.loan_id = l.id "
                           "join organizations b on b.id = l.bank_org_id where b.code = :b and g.approval_status = :a "
                           "order by l.bank_loan_ref limit 1"), {"b": "ANB", "a": "APPROVED"}).one()


def _second_approver(client, auth):
    email = f"approver.{uuid.uuid4().hex[:6]}@anb.demo"
    inv = client.post("/api/v1/admin/users/invite", headers=auth("bank_admin"),
                      json={"email": email, "full_name": "Second Approver", "role_code": "BANK_LOAN_OPS"})
    assert inv.status_code == 201, inv.text
    r = client.post("/api/v1/auth/invitations/accept", json={"token": inv.json()["invitation_token"], "password": PW})
    assert r.status_code == 200, r.text
    tok = client.post("/api/v1/auth/login", json={"email": email, "password": PW}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_guarantor_contacts_masked_and_scoped(client, auth, owner_db):
    lo = _anb_loan_with_guarantor(owner_db)
    gs = client.get(f"/api/v1/loans/{lo.id}/guarantors", headers=auth("loan_ops")).json()
    assert gs and all(g["role"] == "GUARANTOR" for g in gs) and "*" in gs[0]["mobile"]
    assert client.get(f"/api/v1/loans/{lo.id}/guarantors", headers=auth("mfb_ops")).status_code == 404
    assert client.get(f"/api/v1/loans/{lo.id}/guarantors", headers=auth("college_admin")).status_code == 403
    assert client.get(f"/api/v1/loans/{lo.id}/guarantors", headers=auth("field")).status_code == 403


def test_witness_is_separate_and_has_no_liability(client, auth, owner_db):
    lo = _anb_loan_with_guarantor(owner_db)
    w = client.post(f"/api/v1/loans/{lo.id}/witnesses", headers=auth("loan_ops"),
                    json={"full_name": "Selvi Arumugam", "document_ref": "LA-TEST", "witnessed_on": "2021-07-01"})
    assert w.status_code == 201
    body = w.json()
    assert body["role"] == "WITNESS" and body["liability"].startswith("NONE")
    for k in ("guarantee_scope", "guarantee_status", "communication_permitted", "agreement_ref"):
        assert k not in body
    cols = {r[0] for r in owner_db.execute(text("select column_name from information_schema.columns "
                                                "where table_name = :t"), {"t": "witnesses"})}
    assert not cols & {"guarantee_scope", "communication_permitted", "liability_amount"}
    assert client.post(f"/api/v1/loans/{lo.id}/witnesses", headers=auth("investigator"),
                       json={"full_name": "X Y", "document_ref": "LA"}).status_code == 403
    assert client.get(f"/api/v1/loans/{lo.id}/witnesses", headers=auth("investigator")).status_code == 200


def test_guarantor_change_needs_second_user(client, auth, owner_db):
    lo = _anb_loan_with_guarantor(owner_db)
    h = auth("loan_ops")
    r = client.patch(f"/api/v1/guarantors/{lo.gid}", headers=h,
                     json={"city": "Tiruchirappalli", "reason": "Guarantor relocated per bank letter"})
    assert r.status_code == 200 and r.json()["approval_status"] == "PENDING_APPROVAL"
    assert r.json()["city"] != "Tiruchirappalli"
    again = client.patch(f"/api/v1/guarantors/{lo.gid}", headers=h, json={"city": "Salem", "reason": "Second edit try"})
    assert again.json()["error"]["code"] == "PENDING_APPROVAL"
    own = client.post(f"/api/v1/guarantors/{lo.gid}/approve", headers=h, json={"notes": "self approve"})
    assert own.status_code == 409 and own.json()["error"]["code"] == "SOD_MAKER_CHECKER"
    approver = _second_approver(client, auth)
    pend = client.get("/api/v1/guarantor-approvals", headers=approver).json()
    assert any(p["id"] == str(lo.gid) and p["can_approve"] for p in pend)
    ok = client.post(f"/api/v1/guarantors/{lo.gid}/approve", headers=approver, json={"notes": "Bank letter checked"})
    assert ok.status_code == 200 and ok.json()["city"] == "Tiruchirappalli" and ok.json()["approval_status"] == "APPROVED"


def test_guarantor_communication_requires_basis(client, auth, owner_db):
    lo = _anb_loan_with_guarantor(owner_db)
    r = client.post(f"/api/v1/loans/{lo.id}/guarantors", headers=auth("loan_ops"),
                    json={"full_name": "New Guarantor", "agreement_ref": "GA-NEW", "communication_permitted": True})
    assert r.status_code == 400
    r = client.post(f"/api/v1/loans/{lo.id}/guarantors", headers=auth("loan_ops"),
                    json={"full_name": "New Guarantor", "agreement_ref": "GA-NEW"})
    assert r.status_code == 201 and r.json()["approval_status"] == "PENDING_APPROVAL"
    assert os.environ.get("DAPRO_ENV") == "test"
