"""Audit search, chain verification and case reconstruction (FR-AUD, RD 11.3, US-08)."""
from sqlalchemy import text


def test_audit_search_verify_and_no_mutation_routes(client, auth):
    h = auth("auditor")
    ev = client.get("/api/v1/audit/events?action=bank.&size=5", headers=h).json()
    assert ev["total"] >= 1 and all(e["action"].startswith("bank.") for e in ev["items"])
    seq = ev["items"][0]["seq"]
    assert client.delete(f"/api/v1/audit/events/{seq}", headers=h).status_code in (404, 405)
    assert client.patch(f"/api/v1/audit/events/{seq}", json={}, headers=h).status_code in (404, 405)
    v = client.get("/api/v1/audit/verify", headers=h).json()
    assert v["ok"] is True and v["events_checked"] > 0
    assert client.get("/api/v1/audit/checkpoints", headers=h).json()[0]["ok"] is True
    assert client.get("/api/v1/audit/events", headers=auth("loan_ops")).status_code == 403


def test_case_reconstruction_has_completeness(client, auth, owner_db):
    cid = owner_db.execute(text("select c.id from cases c join organizations o on o.id=c.bank_org_id "
                                "where o.code='ANB' limit 1")).scalar()
    if cid is None:  # operations seed may not exist yet in this build; create a minimal case
        row = owner_db.execute(text("select l.id, l.student_id, l.tenant_id, l.bank_org_id from loan_accounts l "
                                    "join organizations o on o.id=l.bank_org_id where o.code='ANB' "
                                    "and l.repayment_status='OVERDUE' limit 1")).one()
        cid = owner_db.execute(text(
            "insert into cases (id, tenant_id, case_ref, student_id, loan_id, bank_org_id, category, reason, source, "
            "priority, status, version, created_at, updated_at) values (gen_random_uuid(), :t, 'CASE-TEST-1', :s, :l, "
            ":b, 'REPAYMENT_FOLLOW_UP', 'test', 'MANUAL', 'MEDIUM', 'NEW', 1, now(), now()) returning id"),
            {"t": row[2], "s": row[1], "l": row[0], "b": row[3]}).scalar()
        owner_db.commit()
    r = client.get(f"/api/v1/audit/cases/{cid}/reconstruction", headers=auth("auditor"))
    assert r.status_code == 200, r.text
    comp = r.json()["completeness"]
    assert comp["status"] in ("COMPLETE", "INCOMPLETE") and comp["checks"]
    assert r.json()["student"]["dapro_ref"]
    assert client.get(f"/api/v1/audit/cases/{cid}/reconstruction", headers=auth("mfb_ops")).status_code == 403
