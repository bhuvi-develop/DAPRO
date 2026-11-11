# DAPRO - API Reference

- Base path: `/api/v1` (through nginx at `http://localhost:8480/api/v1`, or directly at `http://localhost:8410/api/v1`).
- Interactive documentation: `/api/v1/docs` (Swagger UI); schema: `/api/v1/openapi.json`.
- Complete operation list with the permission each requires (160 operations, generated from the code):
  [`api/API_INVENTORY.md`](api/API_INVENTORY.md). Regenerate after changing routes:
  `MSYS_NO_PATHCONV=1 docker compose exec backend sh -c "PYTHONPATH=/app python scripts/gen_docs.py /tmp/docs"`
  then `docker compose cp backend:/tmp/docs/api/API_INVENTORY.md docs/api/`.

## Authentication

```http
POST /api/v1/auth/login        {"email": "...", "password": "...", "tenant_code": null}
-> 200 {"access_token": "...", "token_type": "bearer", ...}  + HttpOnly refresh cookie
-> 200 {"mfa_required": true, "mfa_token": "..."}             then POST /auth/mfa/verify
POST /api/v1/auth/refresh      (cookie) -> {"access_token": "..."}
GET  /api/v1/auth/me           -> user, roles, permissions, organization, environment flags
```

Send `Authorization: Bearer <access_token>` on every other call.

## Conventions

| Topic | Convention |
|---|---|
| Lists | `GET` with `page` (1-based), `size` (default 25, max 200), `q` search, `sort` (`field` or `-field`), module filters; returns `{"items", "total", "page", "size"}` |
| Validation | Pydantic; failures return **400** `VALIDATION_FAILED` with `details: [{field, message}]` |
| Errors | `{"error": {"code", "message", "next_step", "correlation_id", "details"}}`; 401 unauthenticated, 403 missing permission, 404 not found **or out of scope**, 409 business conflict (`INVALID_TRANSITION`, `SOD_MAKER_CHECKER`, `CONFLICT_OF_INTEREST`, version conflict) |
| Correlation | `X-Correlation-ID` accepted or generated, echoed in responses and logs |
| Money | Decimal strings, INR; `null` when masked for the caller's role |
| Freshness | Bank-derived blocks include `freshness: {source, as_of, sync_state}` |
| Dates | ISO 8601; timestamps UTC |
| Rate limiting | Login: 20 attempts per minute per IP and email |

## Main resources

| Area | Endpoints (abbreviated) |
|---|---|
| Admin | `/admin/organizations`, `/admin/org-units`, `/admin/sharing-agreements`, `/admin/users`, `/admin/roles`, `/admin/permissions`, `/admin/sessions`, `/admin/integrations`, `/admin/policies` (+ `/approve`, `/reject`), `/admin/demo/reset` |
| Students | `/students`, `/students/{id}`, `/students/{id}/profile`, `/students/{id}/history`, `/students/imports`, `/students/duplicates` |
| Lifecycle | `/students/{id}/addresses`, `/addresses/{id}/dispute`, `/address-verifications`, `/students/{id}/contacts`, `/students/{id}/contact-preferences`, `/students/{id}/consents`, `/students/{id}/academic`, `/students/{id}/employment` |
| Loans | `/loans`, `/loans/link`, `/loans/{id}` (+ `/schedule`, `/transactions`, `/snapshots`, `/guarantors`, `/witnesses`), `/banks/{bank_org_id}/sync`, `/imports`, `/reconciliation` |
| Repayments | `/repayments/overview`, `/repayments/accounts` |
| Risk | `/risk/indicators` (+ `/decision`, `/assign`), `/risk/rules` (+ `/versions`, `/test`, `/approve`), `/risk/run` |
| Cases and field | `/cases` (+ `/assign`, `/transition`, `/follow-ups`, `/evidence`, `/commitments`, `/visits`), `/field/my-cases`, `/field/review-queue`, `/visits/{id}` (+ `/check-in`, `/check-out`, `/submit`, `/review`) |
| Engagement | `/communications`, `/templates` (+ `/approve`), `/grievances` (+ `/meta`, `/assign`, `/respond`, `/transition`) |
| Borrower portal | `/portal/overview`, `/portal/profile`, `/portal/address`, `/portal/employment`, `/portal/grievances`, `/portal/communications` |
| Insights | `/dashboard/summary`, `/reports/catalog`, `/reports/{code}/run`, `/exports`, `/search`, `/notifications` |
| Audit | `/audit/events`, `/audit/verify`, `/audit/checkpoints`, `/audit/cases/{id}/reconstruction` |
| Operations | `/health` (DB check), `/metrics` (Prometheus, backend port only) |

## Example: grievance lifecycle

```http
POST /api/v1/grievances
{"student_id": "<uuid>", "category": "AMOUNT_DISPUTE", "subject": "EMI already paid",
 "description": "Paid by UPI on the due date.", "channel": "PHONE", "priority": "MEDIUM"}
-> 201 {"ref": "GRV-000123", "status": "SUBMITTED", "due_on": "...", "case_id": "<paused case>", ...}

POST /api/v1/grievances/{id}/transition   {"to": "UNDER_REVIEW"}
POST /api/v1/grievances/{id}/respond      {"message": "Checking with the bank.", "visibility": "BORROWER"}
POST /api/v1/grievances/{id}/transition   {"to": "RESOLVED", "reason": "Bank confirmed the payment."}
```

`channel` is one of STAFF, PHONE, EMAIL, IN_PERSON, LETTER (PORTAL is set automatically for borrowers);
`priority` LOW, MEDIUM, HIGH, CRITICAL; `visibility` BORROWER or INTERNAL; RESOLVED and REJECTED require a reason.
