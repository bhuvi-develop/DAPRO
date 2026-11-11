"""Address history and verification, employment history, contacts, consents (FR-ADR, FR-EMP, AC-07, AC-08)."""
from sqlalchemy import text


def _nbit_anb_student(db):
    return db.execute(text(
        "select s.id from students s join organizations c on c.id = s.college_org_id "
        "join loan_accounts l on l.student_id = s.id join organizations b on b.id = l.bank_org_id "
        "where c.code = :c and b.code = :b and l.link_status = :ls order by s.dapro_ref offset 3 limit 1"),
        {"c": "NBIT", "b": "ANB", "ls": "LINKED"}).scalar()


ADDR = {"kind": "CURRENT", "line1": "No. 12, Lake View Road", "city": "Chennai", "state": "Tamil Nadu",
        "postal_code": "600040", "country": "IN", "source_type": "BORROWER_REPORTED"}


def test_address_history_preserved_and_audited(client, auth, owner_db):
    sid = _nbit_anb_student(owner_db)
    h = auth("college_officer")
    a1 = client.post(f"/api/v1/students/{sid}/addresses", headers=h, json=ADDR)
    assert a1.status_code == 201, a1.text
    a2 = client.post(f"/api/v1/students/{sid}/addresses", headers=h, json={**ADDR, "line1": "No. 99, Park Avenue"})
    assert a2.status_code == 201
    current = client.get(f"/api/v1/students/{sid}/addresses", headers=h).json()
    assert [a["line1"] for a in current if a["kind"] == "CURRENT"] == ["No. 99, Park Avenue"]
    assert client.get(f"/api/v1/students/{sid}/addresses?history=true", headers=h).status_code == 403
    hist = client.get(f"/api/v1/students/{sid}/addresses?history=true", headers=auth("loan_ops")).json()
    old = [a for a in hist if a["id"] == a1.json()["id"]][0]
    assert old["is_current"] is False and old["superseded_at"] is not None
    n = owner_db.execute(text("select count(*) from audit_events where action = :a and target_id = :t"),
                         {"a": "address.history_viewed", "t": str(sid)}).scalar()
    assert n >= 1


def test_verification_workflow(client, auth, owner_db):
    sid = _nbit_anb_student(owner_db)
    a = client.post(f"/api/v1/students/{sid}/addresses", headers=auth("college_officer"),
                    json={**ADDR, "kind": "CORRESPONDENCE", "request_verification": True,
                          "verification_method": "DOCUMENT"}).json()
    assert a["verification"] == "PENDING"
    queue = client.get("/api/v1/address-verifications", headers=auth("loan_ops")).json()
    req = [q for q in queue if q["address_id"] == a["id"]][0]
    body = {"status": "VERIFIED", "notes": "Utility bill checked"}
    assert client.post(f"/api/v1/address-verifications/{req['id']}/outcome", headers=auth("college_officer"),
                       json=body).status_code == 403
    r = client.post(f"/api/v1/address-verifications/{req['id']}/outcome", headers=auth("loan_ops"), json=body)
    assert r.status_code == 200 and r.json()["status"] == "VERIFIED"
    again = client.post(f"/api/v1/address-verifications/{req['id']}/outcome", headers=auth("loan_ops"), json=body)
    assert again.status_code == 409


def test_dispute_address(client, auth, owner_db):
    sid = _nbit_anb_student(owner_db)
    addr = client.get(f"/api/v1/students/{sid}/addresses", headers=auth("college_officer")).json()[0]
    r = client.post(f"/api/v1/addresses/{addr['id']}/dispute", headers=auth("college_officer"),
                    json={"reason": "Borrower says this address is outdated"})
    assert r.json()["verification"] == "DISPUTED"


def test_employment_history_never_creates_risk(client, auth, owner_db):
    sid = _nbit_anb_student(owner_db)
    before = owner_db.execute(text("select count(*) from risk_indicators where student_id = :s"), {"s": sid}).scalar()
    h = auth("college_officer")
    r = client.post(f"/api/v1/students/{sid}/employment", headers=h,
                    json={"status": "UNEMPLOYED", "source": "BORROWER_REPORTED"})
    assert r.status_code == 201 and r.json()["verification"] == "UNVERIFIED"
    r2 = client.post(f"/api/v1/students/{sid}/employment", headers=h,
                     json={"status": "EMPLOYED", "employer_name": "Kaveri Analytics", "source": "BORROWER_REPORTED"})
    hist = client.get(f"/api/v1/students/{sid}/employment", headers=h).json()
    assert hist[0]["id"] == r2.json()["id"] and any(e["id"] == r.json()["id"] and not e["is_current"] for e in hist)
    v = client.post(f"/api/v1/employment/{r2.json()['id']}/verify", headers=h, json={"notes": "Offer letter seen"})
    assert v.json()["verification"] == "VERIFIED" and v.json()["source"] == "BORROWER_REPORTED"
    bad = client.post(f"/api/v1/students/{sid}/employment", headers=h,
                      json={"status": "EMPLOYED", "source": "INSTITUTION_VERIFIED"})
    assert bad.status_code == 400
    after = owner_db.execute(text("select count(*) from risk_indicators where student_id = :s"), {"s": sid}).scalar()
    assert after == before


def test_contacts_and_consents(client, auth, owner_db):
    sid = _nbit_anb_student(owner_db)
    h = auth("college_admin")
    bad = client.post(f"/api/v1/students/{sid}/contacts", headers=h, json={"kind": "EMAIL", "value": "not-an-email"})
    assert bad.status_code == 400
    ok = client.post(f"/api/v1/students/{sid}/contacts", headers=h, json={"kind": "EMAIL", "value": "new.mail@mail.demo"})
    assert ok.status_code == 201
    c = client.post(f"/api/v1/students/{sid}/consents", headers=h,
                    json={"basis": "CONSENT", "purposes": ["ENGAGEMENT"], "notice_version": "PN-2026.1",
                          "source": "PORTAL"}).json()
    w = client.post(f"/api/v1/consents/{c['id']}/withdraw", headers=h).json()
    assert w["active"] is False
    p = client.put(f"/api/v1/students/{sid}/contact-preferences", headers=h,
                   json={"channel": "SMS", "allowed": False, "quiet_start": "20:00", "quiet_end": "09:00"}).json()
    assert p["allowed"] is False and p["quiet_start"] == "20:00"


def test_academic_completion_graduates(client, auth, owner_db):
    sid = owner_db.execute(text("select s.id from students s join organizations c on c.id = s.college_org_id "
                                "where c.code = :c and s.lifecycle_status = :st limit 1"),
                           {"c": "NBIT", "st": "STUDYING"}).scalar()
    r = client.post(f"/api/v1/students/{sid}/academic", headers=auth("college_officer"),
                    json={"programme": "B.E.", "course": "Civil Engineering", "cohort_year": 2022,
                          "enrolment_status": "COMPLETED", "actual_completion": "2026-05-31"})
    assert r.status_code == 201
    s = client.get(f"/api/v1/students/{sid}", headers=auth("college_officer")).json()
    assert s["lifecycle_status"] == "GRADUATED"
