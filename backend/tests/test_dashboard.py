"""Enterprise cockpit and repayment monitoring: backend-derived, role-scoped, financial data masked."""
import time

from sqlalchemy import text


def _kpi(body, key):
    return next((k for k in body["kpis"] if k["key"] == key), None)


def test_dashboard_kpis_match_database_for_bank_user(client, auth, owner_db):
    t0 = time.perf_counter()
    r = client.get("/api/v1/dashboard/summary", headers=auth("loan_ops"))
    elapsed = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200, r.text
    body = r.json()
    q = lambda sql: owner_db.execute(text(sql), {"c": "ANB"}).scalar()  # noqa: E731
    base = "from loan_accounts l join organizations o on o.id=l.bank_org_id where o.code=:c and l.link_status='LINKED'"
    assert _kpi(body, "linked_loans")["value"] == q("select count(*) " + base)
    assert _kpi(body, "overdue_accounts")["value"] == q("select count(*) " + base + " and l.repayment_status='OVERDUE'")
    assert _kpi(body, "current_repayment")["value"] == q("select count(*) " + base + " and l.repayment_status='CURRENT'")
    amount = _kpi(body, "total_overdue_amount")
    expected = q("select coalesce(sum(overdue_amount),0) " + base +
                 " and l.repayment_status='OVERDUE' and l.sync_state='CURRENT'")
    assert amount is not None and float(amount["value"]) == float(expected)
    assert _kpi(body, "overdue_accounts")["link"] == "/loans?repayment_status=OVERDUE"
    assert body["header"]["financial_visible"] is True and body["header"]["last_sync"]
    ch = body["charts"]
    assert len(ch["monthly_repayment_trend"]) == 12 and ch["overdue_ageing"]["approval_label"]
    assert body["operational_health"]["integrations"] and body["activity"]
    print(f"dashboard summary {elapsed:.0f} ms (server compute {body['header']['compute_ms']} ms)")


def test_dashboard_college_and_platform_have_no_financial_amounts(client, auth, owner_db):
    col = client.get("/api/v1/dashboard/summary", headers=auth("college_admin")).json()
    assert _kpi(col, "total_overdue_amount") is None and col["header"]["financial_visible"] is False
    n = owner_db.execute(text("select count(*) from students s join organizations o on o.id=s.college_org_id "
                              "where o.code='NBIT' and s.record_status='ACTIVE'")).scalar()
    assert _kpi(col, "total_students")["value"] == n
    assert all(row["disbursed"] is None for row in col["charts"]["portfolio_by_bank_college"])
    plat = client.get("/api/v1/dashboard/summary", headers=auth("platform")).json()
    assert _kpi(plat, "total_overdue_amount") is None
    assert plat["lists"]["recently_overdue"] == [] and plat["student_intel"]["recently_added"] == []


def test_dashboard_requires_permission_and_valid_period(client, auth):
    assert client.get("/api/v1/dashboard/summary").status_code == 401
    r = client.get("/api/v1/dashboard/summary?from=2026-10-01&to=2026-09-01", headers=auth("loan_ops"))
    assert r.status_code == 400
    ok = client.get("/api/v1/dashboard/summary?from=2026-01-01&to=2026-06-30", headers=auth("loan_ops"))
    assert ok.json()["header"]["period"]["from"] == "2026-01-01"


def test_field_officer_dashboard_is_assignment_scoped(client, auth, owner_db):
    body = client.get("/api/v1/dashboard/summary", headers=auth("field")).json()
    owned = owner_db.execute(text("select count(*) from cases c join users u on u.id=c.owner_id "
                                  "where u.email='karthik.field@anb.demo' and c.status not in ('RESOLVED','CLOSED')")).scalar()
    assert _kpi(body, "open_cases")["value"] == owned
    assert _kpi(body, "total_overdue_amount") is None
