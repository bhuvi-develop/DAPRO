"""Field operations: assigned scope, no location capture, idempotent submit, supervisor review (FR-FLD, AC-11)."""
from sqlalchemy import text

from tests.ops_helpers import uid


def _karthik_case(client, auth):
    items = client.get("/api/v1/field/my-cases", headers=auth("field")).json()["items"]
    assert items, "seeded field officer should have assigned cases"
    return items[0]


def test_my_cases_only_assigned_and_mobile_payload(client, auth):
    page = client.get("/api/v1/field/my-cases", headers=auth("field")).json()
    assert page["settings"]["location_capture_enabled"] is False
    item = page["items"][0]
    assert item["student"]["name"] and "*" in (item["student"]["mobile"] or "*")
    assert client.get("/api/v1/field/my-cases", headers=auth("manager")).status_code == 403


def test_cannot_record_visit_on_unassigned_case(client, auth, owner_db):
    other = owner_db.execute(text("select id from cases where owner_id is distinct from :k and status = :s limit 1"),
                             {"k": uid(owner_db, "karthik.field@anb.demo"), "s": "ASSIGNED"}).scalar()
    r = client.post(f"/api/v1/cases/{other}/visits", headers=auth("field"), json={"purpose": "Check address"})
    assert r.status_code in (403, 404)


def test_visit_flow_check_in_submit_idempotent(client, auth):
    h = auth("field")
    case = _karthik_case(client, auth)
    v = client.post(f"/api/v1/cases/{case['case_id']}/visits", headers=h,
                    json={"purpose": "Verify current address", "client_draft_id": "test-draft-1"}).json()
    again = client.post(f"/api/v1/cases/{case['case_id']}/visits", headers=h,
                        json={"purpose": "Verify current address", "client_draft_id": "test-draft-1"}).json()
    assert again["id"] == v["id"]
    ci = client.post(f"/api/v1/visits/{v['id']}/check-in", headers=h).json()
    assert ci["check_in_at"] and ci["location_captured"] is False
    client.post(f"/api/v1/visits/{v['id']}/check-out", headers=h)
    bad = client.post(f"/api/v1/visits/{v['id']}/submit", headers=h, json={"outcome": "FOUND_HIM", "notes": "xxxxxx"})
    assert bad.status_code == 400
    body = {"outcome": "NO_CONTACT", "notes": "House locked; neighbour confirmed residence.", "client_draft_id": "sub-1"}
    s1 = client.post(f"/api/v1/visits/{v['id']}/submit", headers=h, json=body)
    s2 = client.post(f"/api/v1/visits/{v['id']}/submit", headers=h, json=body)
    assert s1.status_code == 200 and s2.status_code == 200 and s2.json()["id"] == s1.json()["id"]
    assert s1.json()["evidence_quality"] == "OFFICER_OBSERVATION" and s1.json()["status"] == "SUBMITTED"


def test_safety_incident_goes_to_supervisor_review(client, auth):
    h = auth("field")
    case = _karthik_case(client, auth)
    v = client.post(f"/api/v1/cases/{case['case_id']}/visits", headers=h, json={"purpose": "Follow-up visit"}).json()
    r = client.post(f"/api/v1/visits/{v['id']}/submit", headers=h,
                    json={"outcome": "BORROWER_UNAVAILABLE", "notes": "Officer left after argument.",
                          "safety_incident": True})
    assert r.status_code == 400  # incident needs a description
    r = client.post(f"/api/v1/visits/{v['id']}/submit", headers=h,
                    json={"outcome": "BORROWER_UNAVAILABLE", "notes": "Officer left after argument.",
                          "safety_incident": True, "incident_notes": "Raised voices; officer withdrew safely."})
    assert r.json()["review_status"] == "PENDING"
    assert client.get("/api/v1/field/review-queue", headers=h).status_code == 403
    q = client.get("/api/v1/field/review-queue", headers=auth("manager_all")).json()["items"]
    assert any(i["id"] == v["id"] and i["student_name"] for i in q)
    rv = client.post(f"/api/v1/visits/{v['id']}/review", headers=auth("manager_all"),
                     json={"decision": "RETURNED", "notes": "Add who was present."})
    assert rv.status_code == 200 and rv.json()["status"] == "DRAFT"
    again = client.post(f"/api/v1/visits/{v['id']}/review", headers=auth("manager_all"),
                        json={"decision": "APPROVED", "notes": "Second review attempt"})
    assert again.status_code == 409
