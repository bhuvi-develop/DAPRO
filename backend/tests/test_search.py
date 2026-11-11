"""Global search is permission- and scope-filtered."""
from sqlalchemy import text


def test_bank_search_finds_loans(client, auth):
    r = client.get("/api/v1/search?q=ANB-EDU", headers=auth("loan_ops")).json()
    assert set(r) == {"students", "loans", "cases", "grievances"}
    assert r["loans"] and len(r["loans"]) <= 6 and r["loans"][0]["link"].startswith("/loans/")


def test_college_search_scoped(client, auth, owner_db):
    s = owner_db.execute(text("select s.dapro_ref from students s join organizations c "
                              "on c.id = s.college_org_id where c.code = :c limit 1"), {"c": "NBIT"}).one()
    own = client.get(f"/api/v1/search?q={s.dapro_ref}", headers=auth("college_officer")).json()
    assert own["students"] and own["students"][0]["link"].startswith("/students/") and own["cases"] == []
    assert client.get(f"/api/v1/search?q={s.dapro_ref}", headers=auth("rce_admin")).json()["students"] == []
    assert client.get(f"/api/v1/search?q={s.dapro_ref}", headers=auth("iso_college")).json()["students"] == []


def test_short_query_returns_empty(client, auth):
    r = client.get("/api/v1/search?q=a", headers=auth("loan_ops")).json()
    assert all(v == [] for v in r.values())
