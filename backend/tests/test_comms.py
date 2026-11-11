"""Communications: every refusal recorded with a reason; MOCK delivery; lawful guarantor contact (FR-COM, BR-13)."""
from sqlalchemy import text

from tests.ops_helpers import anb_student_with_loan, never_quiet


def _send(client, h, sid, code="EMI_REMINDER", **kw):
    r = client.post("/api/v1/communications", headers=h, json={"student_id": str(sid), "template_code": code, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_reminder_queued_then_delivered_by_mock(client, auth, owner_db):
    sid, _ = anb_student_with_loan(owner_db, "CURRENT", 3)
    never_quiet(owner_db, sid)
    owner_db.execute(text("update consents set withdrawn_at = null where student_id = :s"), {"s": sid})
    owner_db.execute(text("delete from communications where student_id = :s"), {"s": sid})
    owner_db.commit()
    c = _send(client, auth("loan_ops"), sid)
    assert c["status"] == "QUEUED" and c["provider_mode"] == "MOCK" and "*" in c["recipient_masked"]
    from app.core.db import OwnerSessionLocal
    from app.modules.comms.service import dispatch

    db = OwnerSessionLocal()
    dispatch(db)
    db.commit()
    db.close()
    row = client.get(f"/api/v1/students/{sid}/communications", headers=auth("loan_ops")).json()["items"][0]
    assert row["status"] == "DELIVERED" and "not proof of receipt" in row["delivery_note"]


def test_withdrawn_consent_blocks(client, auth, owner_db):
    sid, _ = anb_student_with_loan(owner_db, "CURRENT", 4)
    never_quiet(owner_db, sid)
    owner_db.execute(text("update consents set withdrawn_at = now() where student_id = :s"), {"s": sid})
    owner_db.commit()
    c = _send(client, auth("loan_ops"), sid, "CONTACT_UPDATE_REQUEST")
    assert c["status"] == "BLOCKED" and c["block_reason"].startswith("NO_ACTIVE_CONSENT")
    n = owner_db.execute(text("select count(*) from audit_events where action = :a and target_id = :t"),
                         {"a": "comm.blocked", "t": c["id"]}).scalar()
    assert n == 1


def test_sms_opt_out_and_quiet_hours_block(client, auth, owner_db):
    sid, _ = anb_student_with_loan(owner_db, "CURRENT", 5)
    owner_db.execute(text("update consents set withdrawn_at = null where student_id = :s"), {"s": sid})
    owner_db.execute(text("update contact_preferences set allowed = false where student_id = :s and channel = :c"),
                     {"s": sid, "c": "SMS"})
    owner_db.execute(text("update contact_preferences set quiet_start = :a, quiet_end = :b where student_id = :s "
                          "and channel = :c"), {"a": "00:00", "b": "23:59", "s": sid, "c": "EMAIL"})
    owner_db.commit()
    sms = _send(client, auth("loan_ops"), sid, "EMI_REMINDER_SMS")
    assert sms["block_reason"].startswith("CHANNEL_NOT_PERMITTED")
    email = _send(client, auth("loan_ops"), sid, "EMI_REMINDER")
    assert email["block_reason"].startswith("QUIET_HOURS")


def test_guarantor_requires_lawful_basis(client, auth, owner_db):
    g = owner_db.execute(text("select g.id, l.student_id from guarantors g join loan_accounts l on l.id = g.loan_id "
                              "join organizations o on o.id = l.bank_org_id where o.code = :b "
                              "and g.communication_permitted = false limit 1"), {"b": "ANB"}).one()
    c = _send(client, auth("loan_ops"), g.student_id, "GUARANTOR_NOTICE", recipient_type="GUARANTOR",
              guarantor_id=str(g.id))
    assert c["status"] == "BLOCKED" and c["block_reason"].startswith("NO_LAWFUL_BASIS")
    r = client.post("/api/v1/communications", headers=auth("investigator"),
                    json={"student_id": str(g.student_id), "template_code": "GUARANTOR_NOTICE",
                          "recipient_type": "GUARANTOR", "guarantor_id": str(g.id)})
    assert r.status_code == 403


def test_open_amount_dispute_pauses_reminders(client, auth, owner_db):
    sid, lid = anb_student_with_loan(owner_db, "OVERDUE", 6)
    never_quiet(owner_db, sid)
    owner_db.execute(text("update consents set withdrawn_at = null where student_id = :s"), {"s": sid})
    owner_db.commit()
    g = client.post("/api/v1/grievances", headers=auth("loan_ops"),
                    json={"student_id": str(sid), "loan_id": str(lid), "category": "AMOUNT_DISPUTE",
                          "subject": "Disputes overdue amount", "description": "Borrower says the EMI was paid."})
    assert g.status_code == 201
    c = _send(client, auth("loan_ops"), sid, "EMI_REMINDER")
    assert c["block_reason"].startswith("DISPUTE_PAUSE")


def test_template_needs_second_approver(client, auth):
    body = {"code": "TEST_NOTICE", "name": "Test notice", "channel": "EMAIL", "purpose": "GENERAL",
            "subject": "Hello", "body": "Dear {name}, this is a test notice.", "shared": True}
    t = client.post("/api/v1/templates", headers=auth("bank_admin"), json=body).json()
    assert t["status"] == "DRAFT"
    own = client.post(f"/api/v1/templates/{t['id']}/approve", headers=auth("bank_admin"))
    assert own.status_code == 409 and own.json()["error"]["code"] == "SOD_CONFLICT"
    from tests.conftest import login
    ok = client.post(f"/api/v1/templates/{t['id']}/approve", headers=login(client, "admin@mfb.demo"))
    assert ok.status_code == 200 and ok.json()["status"] == "APPROVED"


def test_college_sees_only_own_college_communications(client, auth, owner_db):
    items = client.get("/api/v1/communications?size=200", headers=auth("college_admin")).json()["items"]
    nbit = owner_db.execute(text("select id from organizations where code = :c"), {"c": "NBIT"}).scalar()
    ids = {r[0] for r in owner_db.execute(text("select id::text from students where college_org_id = :c"),
                                          {"c": nbit}).all()}
    assert all(i["student_id"] in ids for i in items)
