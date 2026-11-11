"""Reports, purpose-logged exports, audit search, chain verification, reconstruction, notifications."""
from sqlalchemy import text


def test_catalog_has_14_reports_with_definitions(client, auth):
    cat = client.get("/api/v1/reports/catalog", headers=auth("loan_ops")).json()
    assert len(cat) == 14
    assert all(c["calculation_definition"] and c["data_source"] for c in cat)
    assert next(c for c in cat if c["code"] == "AUDIT_LOG")["allowed"] is False


def test_every_report_runs_with_meta(client, auth):
    h = auth("auditor")
    for code in ("PORTFOLIO_SUMMARY", "STUDENT_REGISTER", "LOAN_LINKAGE", "REPAYMENT_STATUS", "OVERDUE_AGEING",
                 "DPD_DETAIL", "DATA_FRESHNESS", "CASE_AGEING", "FOLLOWUP_PRODUCTIVITY", "RISK_REVIEW",
                 "FIELD_VISITS", "GRIEVANCES", "INTEGRATION_HEALTH", "AUDIT_LOG"):
        r = client.post(f"/api/v1/reports/{code}/run", json={"filters": {"date_from": "2020-01-01"}}, headers=h)
        assert r.status_code == 200, (code, r.text)
        meta = r.json()["meta"]
        for k in ("as_of", "period", "filters", "source", "definition", "generated_by_role"):
            assert k in meta
        assert r.json()["columns"]


def test_college_report_masks_amounts_and_financial_report_forbidden(client, auth):
    h = auth("college_admin")
    rows = client.post("/api/v1/reports/OVERDUE_AGEING/run", json={}, headers=h).json()["rows"]
    assert all(r["overdue_amount"] is None for r in rows)
    assert client.post("/api/v1/reports/DPD_DETAIL/run", json={}, headers=h).status_code == 403


def test_export_requires_purpose_and_is_audited(client, auth, owner_db):
    h = auth("loan_ops")
    bad = client.post("/api/v1/exports", json={"report_code": "REPAYMENT_STATUS", "purpose": "short"}, headers=h)
    assert bad.status_code == 400
    r = client.post("/api/v1/exports", json={"report_code": "REPAYMENT_STATUS",
                                             "purpose": "Monthly branch repayment review"}, headers=h)
    assert r.status_code == 202, r.text
    job = r.json()
    assert job["status"] == "COMPLETED" and job["sha256"] and job["row_count"] > 0
    n = owner_db.execute(text("select count(*) from audit_events where action='export.created' and target_id=:i"),
                         {"i": job["id"]}).scalar()
    assert n == 1
    d = client.get(f"/api/v1/exports/{job['id']}/download", headers=h)
    assert d.status_code == 200 and "# purpose" in d.text
    assert client.get(f"/api/v1/exports/{job['id']}/download", headers=auth("manager")).status_code == 404
    assert client.get(f"/api/v1/exports/{job['id']}/download", headers=auth("auditor")).status_code == 200
    assert owner_db.execute(text("select count(*) from audit_events where action='export.downloaded' and target_id=:i"),
                            {"i": job["id"]}).scalar() == 2


def test_field_officer_cannot_export(client, auth):
    r = client.post("/api/v1/exports", json={"report_code": "CASE_AGEING", "purpose": "Trying to export cases"},
                    headers=auth("field"))
    assert r.status_code == 403


def test_notifications_contract(client, auth, owner_db):
    uid, tid = owner_db.execute(text("select id, tenant_id from users where email='ravi.ops@anb.demo'")).one()
    owner_db.execute(text("insert into in_app_notifications (id, tenant_id, user_id, kind, title, severity, created_at) "
                          "values (gen_random_uuid(), :t, :u, 'TEST', 'Test notice', 'INFO', now())"), {"t": tid, "u": uid})
    owner_db.commit()
    h = auth("loan_ops")
    lst = client.get("/api/v1/notifications", headers=h).json()
    assert lst["unread"] >= 1 and lst["items"][0]["read_at"] is None
    assert client.get("/api/v1/notifications/unread-count", headers=h).json()["unread"] == lst["unread"]
    nid = lst["items"][0]["id"]
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=auth("mfb_ops")).status_code == 404
    assert client.post(f"/api/v1/notifications/{nid}/read", headers=h).json()["message"]
    client.post("/api/v1/notifications/read-all", headers=h)
    assert client.get("/api/v1/notifications/unread-count", headers=h).json()["unread"] == 0
