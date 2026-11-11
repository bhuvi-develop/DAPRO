"""Student management and Student 360 (FR-STU, AC-01, AC-02, INT-COM-04)."""
import uuid

from sqlalchemy import text


def _student(db, college="NBIT", bank=None):
    sql = ("select s.id, s.dapro_ref, s.full_name, s.dob from students s join organizations c on c.id = s.college_org_id "
           "where c.code = :c and s.record_status = :r")
    if bank:
        sql += " and exists (select 1 from loan_accounts l join organizations b on b.id = l.bank_org_id " \
               "where l.student_id = s.id and b.code = :b and l.link_status = :ls)"
    return db.execute(text(sql + " order by s.dapro_ref limit 1"),
                      {"c": college, "r": "ACTIVE", "b": bank, "ls": "LINKED"}).one()


def test_college_list_is_scoped(client, auth):
    r = client.get("/api/v1/students?size=200", headers=auth("college_admin"))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 50 and {i["college_name"] for i in body["items"]} == {"Northbridge Institute of Technology"}


def test_other_college_gets_404(client, auth, owner_db):
    s = _student(owner_db)
    assert client.get(f"/api/v1/students/{s.id}", headers=auth("rce_admin")).status_code == 404
    assert client.get(f"/api/v1/students/{s.id}/profile", headers=auth("rce_admin")).status_code == 404


def test_cross_tenant_user_cannot_see_demo(client, auth, owner_db):
    s = _student(owner_db)
    assert client.get(f"/api/v1/students/{s.id}", headers=auth("iso_college")).status_code == 404
    refs = {i["dapro_ref"] for i in client.get("/api/v1/students?size=200", headers=auth("iso_college")).json()["items"]}
    assert s.dapro_ref not in refs and all(r.startswith("ISO-") for r in refs)


def test_college_profile_hides_bank_amounts(client, auth, owner_db):
    s = _student(owner_db, bank="ANB")
    p = client.get(f"/api/v1/students/{s.id}/profile", headers=auth("college_admin")).json()
    assert p["loans"] and all(lo["sanctioned_amount"] is None and lo["financial_restricted"] for lo in p["loans"])
    p2 = client.get(f"/api/v1/students/{s.id}/profile", headers=auth("loan_ops")).json()
    assert p2["loans"][0]["sanctioned_amount"] is not None and p2["loans"][0]["freshness"]["source"]
    assert "*" in (p2["student"]["mobile"] or "*")


def test_field_officer_sees_only_assigned(client, auth, owner_db):
    uid = owner_db.execute(text("select id from users where email = :e"), {"e": "karthik.field@anb.demo"}).scalar()
    n = owner_db.execute(text("select count(distinct student_id) from cases where owner_id = :u"), {"u": uid}).scalar()
    assert client.get("/api/v1/students", headers=auth("field")).json()["total"] == n


def test_bank_user_cannot_create(client, auth):
    r = client.post("/api/v1/students", headers=auth("loan_ops"), json={"college_student_id": "X1", "first_name": "A",
                                                                         "last_name": "B"})
    assert r.status_code == 403


def test_create_duplicate_detection_and_review(client, auth, owner_db):
    h = auth("college_admin")
    sid = "NBITT" + uuid.uuid4().hex[:6]
    body = {"college_student_id": sid, "first_name": "Test", "last_name": "Student", "dob": "2004-02-03",
            "email": "test.student@mail.demo", "mobile": "+919812345678", "programme": "B.E.",
            "course": "Civil Engineering", "cohort_year": 2026}
    r = client.post("/api/v1/students", headers=h, json=body)
    assert r.status_code == 201 and r.json()["dapro_ref"].startswith("DAP-")
    assert client.post("/api/v1/students", headers=h, json=body).json()["error"]["code"] == "DUPLICATE_STUDENT_ID"
    body2 = {**body, "college_student_id": sid + "B"}
    r = client.post("/api/v1/students", headers=h, json=body2)
    assert r.status_code == 409 and r.json()["error"]["code"] == "POSSIBLE_DUPLICATE"
    r = client.post("/api/v1/students", headers=h, json={**body2, "confirm_not_duplicate": True})
    assert r.status_code == 201
    dups = client.get("/api/v1/students/duplicates", headers=h).json()
    mine = [d for d in dups if d["student"]["college_student_id"] == sid + "B"]
    assert mine
    r = client.post(f"/api/v1/students/duplicates/{mine[0]['id']}/resolve", headers=h,
                    json={"decision": "NOT_DUPLICATE", "notes": "Different person, verified documents"})
    assert r.json()["status"] == "NOT_DUPLICATE"


def test_update_requires_version_and_keeps_history(client, auth, owner_db):
    h = auth("college_admin")
    s = client.get("/api/v1/students?size=1&sort=-created_at", headers=h).json()["items"][0]
    patch = {"last_name": "Corrected", "reason": "Spelling corrected from certificate"}
    assert client.patch(f"/api/v1/students/{s['id']}", headers=h, json=patch).status_code == 428
    assert client.patch(f"/api/v1/students/{s['id']}", headers={**h, "If-Match": "999"}, json=patch).status_code == 412
    r = client.patch(f"/api/v1/students/{s['id']}", headers={**h, "If-Match": str(s["version"])}, json=patch)
    assert r.status_code == 200 and r.json()["version"] == s["version"] + 1
    hist = client.get(f"/api/v1/students/{s['id']}/history", headers=h).json()
    assert hist[0]["field"] == "last_name" and hist[0]["old_value"] == s["last_name"]


def test_csv_import_flow(client, auth):
    h = auth("college_admin")
    assert "college_student_id" in client.get("/api/v1/students/imports/template", headers=h).text
    uid = uuid.uuid4().hex[:5]
    csv = ("college_student_id,first_name,last_name,dob,email,mobile,programme,course,cohort_year\n"
           f"IMP{uid}1,Asha,Kumar,2006-01-02,asha{uid}@mail.demo,+919800000001,B.E.,Civil Engineering,2026\n"
           f"IMP{uid}2,Bala,Raman,bad-date,bala{uid}@mail.demo,+919800000002,B.E.,Civil Engineering,2026\n")
    r = client.post("/api/v1/students/imports", headers=h, files={"file": ("cohort.csv", csv, "text/csv")})
    assert r.status_code == 202, r.text
    b = r.json()
    assert b["status"] == "VALIDATED" and b["valid_rows"] == 1 and b["error_rows"] == 1
    r = client.post(f"/api/v1/students/imports/{b['id']}/apply", headers=h)
    assert r.json()["status"] == "APPLIED" and r.json()["applied_rows"] == 1
    r = client.post("/api/v1/students/imports", headers=h, files={"file": ("again.csv", csv, "text/csv")})
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_IMPORT"
