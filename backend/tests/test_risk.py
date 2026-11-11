"""Risk intelligence: explainable, neutral, human-reviewed indicators (FR-RSK-01..09, AC-08, AC-10)."""
from sqlalchemy import select, text

from app.models.loans import LoanAccount
from app.models.ops import RiskIndicator, RiskRule
from app.modules.risk import engine
from tests.ops_helpers import uid


def _tenant(db):
    return db.execute(text("select id from tenants where code = :c"), {"c": "DEMO"}).scalar()


def test_indicator_wording_is_neutral(owner_db):
    rows = owner_db.execute(select(RiskIndicator.title, RiskIndicator.explanation)).all()
    assert rows
    for title, expl in rows:
        low = (title + " " + expl).lower()
        assert not any(w in low for w in ("abscond", "defaulter", "fraud")), title


def test_employment_status_alone_never_triggers_financial_indicator(owner_db):
    """AC-08: an UNEMPLOYED borrower with a current loan gets no delinquency indicator."""
    loan = owner_db.execute(select(LoanAccount).where(LoanAccount.repayment_status == "CURRENT",
                                                      LoanAccount.dpd == 0)).scalars().first()
    owner_db.execute(text("update students set lifecycle_status = :s where id = :i"),
                     {"s": "UNEMPLOYED", "i": loan.student_id})
    rules = engine.active_rules(owner_db)
    for code in ("REPAYMENT_OVERDUE", "REPEATED_OVERDUE"):
        hits = engine.rule_hits(owner_db, rules[code])
        assert all(h["loan_id"] != loan.id for h in hits)
        assert all(owner_db.get(LoanAccount, h["loan_id"]).dpd for h in hits)


def test_stale_data_is_a_data_alert_not_delinquency(owner_db):
    loan = owner_db.execute(select(LoanAccount).where(LoanAccount.repayment_status == "OVERDUE")).scalars().first()
    loan.sync_state = "STALE"
    owner_db.flush()
    rules = engine.active_rules(owner_db)
    assert all(h["loan_id"] != loan.id for h in engine.rule_hits(owner_db, rules["REPAYMENT_OVERDUE"]))
    assert any(h["loan_id"] == loan.id for h in engine.rule_hits(owner_db, rules["DATA_STALE"]))


def test_reevaluation_does_not_duplicate(owner_db):
    tid = _tenant(owner_db)
    owner_db.info["tenant_id"] = str(tid)
    engine.evaluate_tenant(owner_db, tid)  # absorb state changes made by earlier test modules
    stats = engine.evaluate_tenant(owner_db, tid)
    assert stats["created"] == 0


def test_indicator_detail_is_explainable(client, auth):
    """AC-10: trigger, evidence, rule version and review history are shown."""
    h = auth("manager_all")
    page = client.get("/api/v1/risk/indicators?status=open&rule_code=REPAYMENT_OVERDUE", headers=h).json()
    assert page["total"] > 0 and page["items"][0]["student_name"]
    d = client.get(f"/api/v1/risk/indicators/{page['items'][0]['id']}", headers=h).json()
    assert d["rule"]["version"] >= 1 and d["evidence"] and d["evidence"][0]["source"]
    assert "reviews" in d and "not legal findings" in d["not_a_finding"]


def test_decision_requires_rationale_and_creates_case(client, auth):
    h = auth("manager_all")
    ind = client.get("/api/v1/risk/indicators?status=OPEN&rule_code=REPEATED_OVERDUE", headers=h).json()["items"][0]
    r = client.post(f"/api/v1/risk/indicators/{ind['id']}/decision", headers=h,
                    json={"decision": "CREATE_CASE", "rationale": "short"})
    assert r.status_code == 400
    r = client.post(f"/api/v1/risk/indicators/{ind['id']}/decision", headers=h,
                    json={"decision": "CREATE_CASE", "rationale": "Bank data reviewed; repeated overdue confirmed.",
                          "priority": "HIGH"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ACTIONED" and body["case_id"] and body["reviews"][0]["decision"] == "CREATE_CASE"
    case = client.get(f"/api/v1/cases/{body['case_id']}", headers=h).json()
    assert case["source"] == "RISK_INDICATOR" and case["status"] == "NEW"
    again = client.post(f"/api/v1/risk/indicators/{ind['id']}/decision", headers=h,
                        json={"decision": "DISMISS", "rationale": "Trying to rewrite a decided indicator."})
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_TRANSITION"


def test_field_officer_cannot_decide(client, auth):
    ind = client.get("/api/v1/risk/indicators", headers=auth("manager_all")).json()["items"][0]
    r = client.post(f"/api/v1/risk/indicators/{ind['id']}/decision", headers=auth("field"),
                    json={"decision": "DISMISS", "rationale": "Field officers have no decision right."})
    assert r.status_code == 403


def test_rule_versioning_with_second_approver(client, auth, owner_db):
    r = client.post("/api/v1/risk/rules/REPAYMENT_OVERDUE/versions", headers=auth("manager"),
                    json={"params": {"min_dpd": 5}, "severity": "MEDIUM", "change_reason": "Bank asked for 5-day threshold"})
    assert r.status_code == 201 and r.json()["status"] == "DRAFT"
    rid = r.json()["id"]
    test = client.post(f"/api/v1/risk/rules/{rid}/test", headers=auth("manager")).json()
    assert "would_trigger" in test
    assert client.post(f"/api/v1/risk/rules/{rid}/approve", headers=auth("manager")).status_code == 403
    ok = client.post(f"/api/v1/risk/rules/{rid}/approve", headers=auth("loan_ops"))
    assert ok.status_code == 200 and ok.json()["status"] == "ACTIVE"
    statuses = owner_db.execute(select(RiskRule.version, RiskRule.status).where(
        RiskRule.code == "REPAYMENT_OVERDUE").order_by(RiskRule.version)).all()
    assert [s for _, s in statuses][-2:] == ["RETIRED", "ACTIVE"]


def test_rule_author_cannot_approve_own_version(client, auth, owner_db):
    ravi = uid(owner_db, "ravi.ops@anb.demo")
    tid = _tenant(owner_db)
    cur = owner_db.execute(select(RiskRule).where(RiskRule.code == "DATA_STALE")).scalars().first()
    draft = RiskRule(tenant_id=tid, code="DATA_STALE", version=99, name=cur.name, category=cur.category,
                     description=cur.description, params={}, severity="LOW", recommended_action="x",
                     status="DRAFT", created_by=ravi)
    owner_db.add(draft)
    owner_db.commit()
    r = client.post(f"/api/v1/risk/rules/{draft.id}/approve", headers=auth("loan_ops"))
    assert r.status_code == 409 and r.json()["error"]["code"] == "SOD_CONFLICT"
