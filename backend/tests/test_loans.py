"""Loan linkage, bank mirror access control, sync and reconciliation (FR-LON, AC-02, AC-04, RD 16.1)."""
from sqlalchemy import text

OPS = {"ANB": "loan_ops", "MFB": "mfb_ops"}


def _loan(db, bank="ANB", branch=None):
    sql = ("select l.id from loan_accounts l join organizations o on o.id=l.bank_org_id "
           "left join org_units u on u.id=l.branch_unit_id where o.code=:b and l.link_status=:s")
    if branch:
        sql += " and u.code=:u"
    return str(db.execute(text(sql + " limit 1"), {"b": bank, "s": "LINKED", "u": branch}).scalar())


def _unlinked(db):
    """A mock bank record with no DAPRO loan whose borrower matches a student without any loan."""
    return db.execute(text(
        "select m.bank_loan_ref, m.bank_org_id, o.code, s.id from mock_bank_records m "
        "join organizations o on o.id=m.bank_org_id join tenants t on t.id=m.tenant_id and t.code=:t "
        "join students s on s.full_name=m.borrower_name and s.dob=m.borrower_dob and s.tenant_id=m.tenant_id "
        "where not exists (select 1 from loan_accounts l where l.bank_loan_ref=m.bank_loan_ref) "
        "and not exists (select 1 from loan_accounts l where l.student_id=s.id) order by m.bank_loan_ref"),
        {"t": "DEMO"}).all()


def test_college_user_sees_no_financial_amounts(client, auth):
    r = client.get("/api/v1/loans?size=50", headers=auth("college_admin"))
    assert r.status_code == 200 and r.json()["total"] > 0
    for it in r.json()["items"]:
        assert it["financial_restricted"] is True
        assert it["overdue_amount"] is None and it["sanctioned_amount"] is None and it["dpd"] is None


def test_bank_user_sees_amounts_with_freshness(client, auth):
    r = client.get("/api/v1/loans?repayment_status=OVERDUE&sort=-dpd", headers=auth("loan_ops"))
    items = r.json()["items"]
    assert items and items[0]["overdue_amount"] is not None
    assert items[0]["freshness"]["source"] == "MOCK_BANK_FEED" and items[0]["freshness"]["as_of"]
    assert items[0]["dpd"] >= items[-1]["dpd"]


def test_cross_bank_access_denied(client, auth, owner_db):
    lid = _loan(owner_db, "ANB")
    assert client.get(f"/api/v1/loans/{lid}", headers=auth("mfb_ops")).status_code == 404
    assert client.get(f"/api/v1/loans/{lid}", headers=auth("loan_ops")).status_code == 200


def test_branch_scoped_manager(client, auth, owner_db):
    rsp = _loan(owner_db, "ANB", "ANB-RSP")
    ann = _loan(owner_db, "ANB", "ANB-ANN")
    assert client.get(f"/api/v1/loans/{rsp}", headers=auth("manager")).status_code == 404
    assert client.get(f"/api/v1/loans/{ann}", headers=auth("manager")).status_code == 200
    assert client.get(f"/api/v1/loans/{rsp}", headers=auth("manager_all")).status_code == 200


def test_loan_detail_schedule_transactions(client, auth, owner_db):
    lid = str(owner_db.execute(text("select l.id from loan_accounts l join organizations o on o.id=l.bank_org_id "
                                    "where o.code='ANB' and l.repayment_status='OVERDUE' limit 1")).scalar())
    d = client.get(f"/api/v1/loans/{lid}", headers=auth("loan_ops")).json()
    assert d["snapshot"]["freshness"]["source"] == "MOCK_BANK_FEED" and d["guarantors"] is not None
    s = client.get(f"/api/v1/loans/{lid}/schedule", headers=auth("loan_ops")).json()
    assert s["versions"] and s["instalments"]
    assert client.get(f"/api/v1/loans/{lid}/transactions", headers=auth("loan_ops")).status_code == 200
    assert client.get(f"/api/v1/loans/{lid}/schedule", headers=auth("college_admin")).status_code == 403


def test_college_cannot_modify_bank_fields(client, auth, owner_db):
    """AC-02: no mutation route exists for bank-owned fields; link attempts by college users are refused and audited."""
    lid = _loan(owner_db, "ANB")
    h = auth("college_admin")
    assert client.patch(f"/api/v1/loans/{lid}", json={"overdue_amount": "0"}, headers=h).status_code == 405
    assert client.put(f"/api/v1/loans/{lid}", json={"overdue_amount": "0"}, headers=h).status_code == 405
    r = client.post("/api/v1/loans/link", json={"student_id": lid, "bank_org_id": lid, "bank_loan_ref": "X-1"},
                    headers=h)
    assert r.status_code == 403
    n = owner_db.execute(text("select count(*) from audit_events where action=:a and outcome=:o "
                              "and payload->>'permission'=:p"),
                         {"a": "access.denied", "o": "DENIED", "p": "loan:link"}).scalar()
    assert n >= 1


def test_link_not_found_and_duplicate(client, auth, owner_db):
    anb = str(owner_db.execute(text("select id from organizations where code=:c"), {"c": "ANB"}).scalar())
    row = owner_db.execute(text("select l.bank_loan_ref, s.id from loan_accounts l join organizations o on "
                                "o.id=l.bank_org_id join students s on s.tenant_id=l.tenant_id and s.id<>l.student_id "
                                "where o.code=:c and l.link_status=:st limit 1"), {"c": "ANB", "st": "LINKED"}).one()
    h = auth("loan_ops")
    r = client.post("/api/v1/loans/link", json={"student_id": str(row[1]), "bank_org_id": anb,
                                                "bank_loan_ref": "ANB-EDU-0000-99999"}, headers=h)
    assert r.status_code == 422 and r.json()["error"]["code"] == "BANK_REFERENCE_NOT_FOUND"
    r = client.post("/api/v1/loans/link", json={"student_id": str(row[1]), "bank_org_id": anb,
                                                "bank_loan_ref": row[0]}, headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DUPLICATE_REFERENCE"


def test_link_happy_path_syncs_bank_data(client, auth, owner_db):
    cands = _unlinked(owner_db)
    assert cands, "seed should contain unlinked bank loans"
    ref, bank_id, code, sid = cands[0]
    r = client.post("/api/v1/loans/link", json={"student_id": str(sid), "bank_org_id": str(bank_id),
                                                "bank_loan_ref": ref}, headers=auth(OPS[code]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["link_status"] == "LINKED" and body["sync_status"] == "APPLIED"
    d = client.get(f"/api/v1/loans/{body['loan_id']}", headers=auth(OPS[code])).json()
    assert d["sync_state"] == "CURRENT" and d["link_validation"]["name_match"] is True


def test_ambiguous_link_goes_to_reconciliation_then_confirm(client, auth, owner_db):
    ref, bank_id, code, sid = _unlinked(owner_db)[0]
    other = owner_db.execute(text(
        "select s.id from students s join tenants t on t.id=s.tenant_id and t.code=:t where s.id<>:sid "
        "and not exists (select 1 from loan_accounts l where l.student_id=s.id) and s.dob is not null limit 1"),
        {"t": "DEMO", "sid": sid}).scalar()
    h = auth(OPS[code])
    r = client.post("/api/v1/loans/link", json={"student_id": str(other), "bank_org_id": str(bank_id),
                                                "bank_loan_ref": ref}, headers=h)
    assert r.status_code == 200 and r.json()["link_status"] == "PENDING_REVIEW"
    q = client.get("/api/v1/reconciliation?kind=AMBIGUOUS_LINK&size=100", headers=h).json()
    item = next(i for i in q["items"] if i["loan_id"] == r.json()["loan_id"])
    bad = client.post(f"/api/v1/reconciliation/{item['id']}/resolve",
                      json={"action": "DISMISS", "resolution": "not allowed for this kind"}, headers=h)
    assert bad.status_code == 400
    ok = client.post(f"/api/v1/reconciliation/{item['id']}/resolve",
                     json={"action": "CONFIRM_LINK", "resolution": "Verified identity documents with branch"},
                     headers=h)
    assert ok.status_code == 200 and ok.json()["status"] == "RESOLVED"
    d = client.get(f"/api/v1/loans/{r.json()['loan_id']}", headers=h).json()
    assert d["link_status"] == "LINKED"


def test_sync_endpoint_scoped_to_own_bank(client, auth, owner_db):
    ids = dict(owner_db.execute(text("select code, id::text from organizations where code in ('ANB','MFB')")).all())
    assert client.post(f"/api/v1/banks/{ids['MFB']}/sync", headers=auth("loan_ops")).status_code == 403
    r = client.post(f"/api/v1/banks/{ids['ANB']}/sync", headers=auth("loan_ops"))
    assert r.status_code == 202 and r.json()["status"] == "APPLIED", r.text
    b = client.get(f"/api/v1/imports/{r.json()['batch_id']}", headers=auth("loan_ops")).json()
    assert b["summary"]["transactions_new"] == 0
    assert client.get(f"/api/v1/imports/{r.json()['batch_id']}", headers=auth("mfb_ops")).status_code == 404
