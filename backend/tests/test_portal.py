"""Borrower portal: own records only, bank-sourced figures with freshness (FR-BRW-01)."""
from sqlalchemy import text

from tests.conftest import login
from tests.ops_helpers import borrowers


def test_overview_has_freshness_and_profile(client, owner_db):
    email, sid = borrowers(owner_db)[1]
    h = login(client, email)
    ov = client.get("/api/v1/portal/overview", headers=h).json()
    assert ov["student"]["id"] == sid and ov["loans"]
    assert set(ov["loans"][0]["freshness"]) == {"source", "as_of", "sync_state"}
    prof = client.get("/api/v1/portal/profile", headers=h).json()
    assert prof["dapro_ref"] and "primary_mobile" in prof["correctable_fields"]


def test_address_and_employment_updates_are_borrower_reported(client, owner_db):
    email, sid = borrowers(owner_db)[2]
    h = login(client, email)
    a = client.post("/api/v1/portal/address", headers=h,
                    json={"kind": "CURRENT", "line1": "12 Lake Road", "city": "Bengaluru", "country": "IN"})
    assert a.status_code == 201 and a.json()["verification"] == "UNVERIFIED"
    assert a.json()["source"] == "BORROWER_REPORTED"
    n = owner_db.execute(text("select count(*) from student_addresses where student_id = :s and kind = :k "
                              "and is_current"), {"s": sid, "k": "CURRENT"}).scalar()
    assert n == 1
    e = client.post("/api/v1/portal/employment", headers=h, json={"status": "EMPLOYED", "employer_name": "Acme"})
    assert e.status_code == 201 and e.json()["verification"] == "UNVERIFIED"


def test_borrower_cannot_reach_other_records(client, owner_db, auth):
    email, sid = borrowers(owner_db)[0]
    h = login(client, email)
    other = owner_db.execute(text("select id from students where id <> :s limit 1"), {"s": sid}).scalar()
    assert client.get(f"/api/v1/students/{other}/communications", headers=h).status_code == 403
    assert client.get("/api/v1/cases", headers=h).status_code == 403
    gid = owner_db.execute(text("select id from grievances where student_id <> :s limit 1"), {"s": sid}).scalar()
    assert client.get(f"/api/v1/portal/grievances/{gid}", headers=h).status_code == 404
    r = client.post("/api/v1/portal/grievances", headers=h,
                    json={"category": "OTHER", "subject": "Statement copy", "description": "Need a statement copy."})
    assert r.status_code == 201 and r.json()["student_id"] == sid
    assert client.get("/api/v1/portal/overview", headers=auth("loan_ops")).status_code == 403
