"""Repayment monitoring views (FR-REP-03/06/07/10, BR-03)."""
from sqlalchemy import text


def test_repayment_overview_and_accounts(client, auth):
    h = auth("loan_ops")
    o = client.get("/api/v1/repayments/overview", headers=h).json()
    assert o["status_counts"] and o["freshness"]["source"] == "MOCK_BANK_FEED" and "unknown_note" in o
    assert all(u["status"] != "PAID" for u in o["upcoming"])
    a = client.get("/api/v1/repayments/accounts?dpd_bucket=DPD_90_PLUS&size=5", headers=h).json()
    assert a["total"] >= 1 and all(i["dpd_bucket"] == "DPD_90_PLUS" for i in a["items"])
    assert client.get("/api/v1/repayments/overview", headers=auth("college_admin")).status_code == 403


def test_stale_loans_never_reported_as_paid_or_zero(client, auth, owner_db):
    stale = owner_db.execute(text("select count(*) from loan_accounts where sync_state<>'CURRENT' "
                                  "and repayment_status in ('CURRENT','PAID') and link_status='LINKED'")).scalar()
    assert stale == 0
