"""Administration and IAM: invitation lifecycle, SoD, status changes, policies, integrations, demo reset."""
import uuid

PW = "Invited@2026x"


def _invite(client, auth, who="bank_admin", role="INVESTIGATION_OFFICER", domain="anb.demo"):
    email = f"user.{uuid.uuid4().hex[:6]}@{domain}"
    r = client.post("/api/v1/admin/users/invite", headers=auth(who),
                    json={"email": email, "full_name": "Invited Person", "role_code": role})
    assert r.status_code == 201, r.text
    return email, r.json()


def _login(client, email):
    return client.post("/api/v1/auth/login", json={"email": email, "password": PW})


def test_invitation_flow_and_status_lifecycle(client, auth):
    email, inv = _invite(client, auth)
    assert inv["user"]["status"] == "INVITED" and inv["invitation_token"]
    assert _login(client, email).status_code == 401
    weak = client.post("/api/v1/auth/invitations/accept",
                       json={"token": inv["invitation_token"], "password": "weakpassword"})
    assert weak.status_code == 400
    assert client.post("/api/v1/auth/invitations/accept",
                       json={"token": inv["invitation_token"], "password": PW}).status_code == 200
    assert client.post("/api/v1/auth/invitations/accept",
                       json={"token": inv["invitation_token"], "password": PW}).status_code == 400
    tok = _login(client, email)
    assert tok.status_code == 200
    uid, h = inv["user"]["id"], auth("bank_admin")
    s = client.post(f"/api/v1/admin/users/{uid}/suspend", headers=h, json={"reason": "Leave of absence"})
    assert s.json()["status"] == "SUSPENDED"
    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + tok.json()["access_token"]})
    assert me.status_code == 401
    assert _login(client, email).status_code == 401
    a = client.post(f"/api/v1/admin/users/{uid}/activate", headers=h, json={"reason": "Returned"})
    assert a.json()["status"] == "ACTIVE" and _login(client, email).status_code == 200


def test_cannot_suspend_self(client, auth):
    me = client.get("/api/v1/auth/me", headers=auth("bank_admin")).json()
    r = client.post(f"/api/v1/admin/users/{me['id']}/suspend", headers=auth("bank_admin"), json={"reason": "test"})
    assert r.status_code == 409


def test_sod_conflict_rejected(client, auth):
    _, inv = _invite(client, auth)
    r = client.put(f"/api/v1/admin/users/{inv['user']['id']}/roles", headers=auth("bank_admin"),
                   json={"role_codes": ["BANK_ADMIN", "BANK_LOAN_OPS"], "reason": "Combine duties"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "SOD_CONFLICT"
    ok = client.put(f"/api/v1/admin/users/{inv['user']['id']}/roles", headers=auth("bank_admin"),
                    json={"role_codes": ["COLLECTIONS_MANAGER"], "reason": "Promotion to manager"})
    assert ok.status_code == 200 and ok.json()["roles"] == ["COLLECTIONS_MANAGER"]


def test_role_must_fit_org_and_scope(client, auth):
    r = client.post("/api/v1/admin/users/invite", headers=auth("bank_admin"),
                    json={"email": f"x{uuid.uuid4().hex[:5]}@anb.demo", "full_name": "Wrong Role",
                          "role_code": "COLLEGE_ADMIN"})
    assert r.status_code == 400
    r = client.post("/api/v1/admin/users/invite", headers=auth("bank_admin"),
                    json={"email": f"x{uuid.uuid4().hex[:5]}@anb.demo", "full_name": "Platform",
                          "role_code": "PLATFORM_ADMIN"})
    assert r.status_code == 403
    users = client.get("/api/v1/admin/users?size=200", headers=auth("college_admin")).json()["items"]
    assert users and {u["org_name"] for u in users} == {"Northbridge Institute of Technology"}
    all_users = client.get("/api/v1/admin/users?size=200", headers=auth("platform")).json()
    assert all_users["total"] > len(users)
    assert client.get("/api/v1/admin/users", headers=auth("loan_ops")).status_code == 403


def test_org_management_permissions(client, auth):
    body = {"type": "COLLEGE", "code": "T" + uuid.uuid4().hex[:6].upper(), "name": "Test Polytechnic"}
    assert client.post("/api/v1/admin/organizations", headers=auth("college_admin"), json=body).status_code == 403
    assert client.post("/api/v1/admin/organizations", headers=auth("platform"), json=body).status_code == 201
    assert client.post("/api/v1/admin/organizations", headers=auth("platform"), json=body).status_code == 409
    orgs = client.get("/api/v1/admin/organizations", headers=auth("loan_ops")).json()
    assert any(o["code"] == "NBIT" for o in orgs)


def test_policy_maker_checker(client, auth):
    pol = client.get("/api/v1/admin/policies", headers=auth("bank_admin")).json()
    cur = [p for p in pol if p["key"] == "DATA_FRESHNESS" and p["status"] == "ACTIVE"][0]
    r = client.post("/api/v1/admin/policies", headers=auth("bank_admin"),
                    json={"key": "DATA_FRESHNESS", "value": {"stale_after_hours": 36}, "effective_from": "2026-01-01",
                          "reason": "Bank requests tighter freshness"})
    assert r.status_code == 201 and r.json()["status"] == "DRAFT"
    pid = r.json()["id"]
    own = client.post(f"/api/v1/admin/policies/{pid}/approve", headers=auth("bank_admin"), json={"reason": "self"})
    assert own.status_code == 409
    ok = client.post(f"/api/v1/admin/policies/{pid}/approve", headers=auth("admin@mfb.demo"),
                     json={"reason": "Reviewed and approved"})
    assert ok.json()["status"] == "ACTIVE"
    after = client.get("/api/v1/admin/policies", headers=auth("bank_admin")).json()
    assert [p for p in after if p["id"] == cur["id"]][0]["status"] == "SUPERSEDED"
    bad = client.post("/api/v1/admin/policies", headers=auth("bank_admin"),
                      json={"key": "UNKNOWN", "value": {}, "effective_from": "2026-01-01", "reason": "invalid key"})
    assert bad.status_code == 400


def test_integrations_scope_and_live_guard(client, auth):
    h = auth("bank_admin")
    feed = [i for i in client.get("/api/v1/admin/integrations", headers=h).json() if i["kind"] == "BANK_LOAN_FEED"]
    assert len(feed) == 1 and feed[0]["is_mock"]
    live = client.patch(f"/api/v1/admin/integrations/{feed[0]['id']}", headers=h, json={"mode": "LIVE"})
    assert live.status_code == 409 and live.json()["error"]["code"] == "LIVE_NOT_AVAILABLE"
    on = client.patch(f"/api/v1/admin/integrations/{feed[0]['id']}", headers=h, json={"simulate_failure": True})
    assert on.json()["simulate_failure"] is True
    client.patch(f"/api/v1/admin/integrations/{feed[0]['id']}", headers=h, json={"simulate_failure": False})
    other = [i for i in client.get("/api/v1/admin/integrations", headers=auth("platform")).json()
             if i["kind"] == "BANK_LOAN_FEED" and i["id"] != feed[0]["id"]][0]
    r = client.patch(f"/api/v1/admin/integrations/{other['id']}", headers=h, json={"refresh_interval_hours": 12})
    assert r.status_code == 404


def test_roles_catalogue_and_demo_reset_guard(client, auth):
    cat = client.get("/api/v1/admin/permissions", headers=auth("auditor")).json()
    assert "FIELD_OFFICER" in cat["matrix"] and cat["sod_conflicts"]
    assert client.post("/api/v1/admin/demo/reset", headers=auth("college_admin"),
                       json={"confirm": "RESET DEMO DATA"}).status_code == 403
    assert client.post("/api/v1/admin/demo/reset", headers=auth("platform"), json={"confirm": "reset"}).status_code == 400


def test_sessions_admin(client, auth):
    sessions = client.get("/api/v1/admin/sessions", headers=auth("bank_admin")).json()
    assert sessions and all(s["email"].endswith("anb.demo") for s in sessions)
