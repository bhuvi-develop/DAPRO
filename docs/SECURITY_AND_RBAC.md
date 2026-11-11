# DAPRO - Security and Role-Based Access Control

All authorization is enforced **server-side**. The UI hides unavailable actions only for clarity.

## Authentication and sessions

| Control | Implementation |
|---|---|
| Passwords | argon2 hashing (`core/security.py`); minimum 10 characters plus the `password_policy` checks on invitation acceptance and change |
| Access token | HS256 JWT, 15 minutes, held in browser memory only (never localStorage) |
| Refresh token | HttpOnly, `SameSite=Strict` cookie scoped to `/api/v1/auth`, 12 hours; `Secure` required outside demo |
| Session idle timeout | 60 minutes; sessions listed and revocable by the user and by `session:manage` admins |
| Brute force | 20 login attempts per minute per IP+email; lockout after 5 failures for 15 minutes; unlock by admin |
| MFA | TOTP enrolment and verification available; enforcement for privileged roles pending OD-20 |
| Secrets | Only from environment variables; `.env` is git-ignored; the API refuses default secrets outside demo/dev/test |

## Authorization layers

1. **Permission** per route: `require("perm")` dependency; deny by default; refusals are audited.
   `test_every_route_declares_permission` fails the build for an unprotected route.
2. **Tenant isolation** in PostgreSQL row-level security (42 tables), bound per transaction.
3. **Organization / branch / assignment scope** in services (`core/scope.py`): college users see their college's
   students; bank users see their bank's loans and the linked students; branch users see their unit subtree;
   field officers see only assigned cases; borrowers see only their own record (portal endpoints are pinned to
   the caller's `student_id`). Out-of-scope records return 404, not 403, so existence is not disclosed.
4. **Field masking** (`core/masking.py`): bank amounts require `loan:financial`; full contact details require
   `student:pii_full`; address history requires `address:history`.
5. **Segregation of duties**: role assignment rejects `user:manage` combined with `risk:decide`, `case:close`
   or `loan:financial`. **Maker-checker** (second user) for policy versions, risk rule versions, notification
   templates and guarantor changes; the maker can neither approve nor reject their own proposal.
6. **Conflict of interest**: the staff member a grievance is about cannot be assigned to or act on it.

## Roles (proposed; final matrix pending client approval, RD section 6)

| Role | Organization types | Permissions | Bank amounts |
|---|---|---|---|
| PLATFORM_ADMIN | PLATFORM | 12 | No |
| COLLEGE_ADMIN | COLLEGE | 23 | No |
| COLLEGE_OFFICER | COLLEGE | 12 | No |
| BANK_ADMIN | BANK, NBFC | 14 | No |
| BANK_LOAN_OPS | BANK, NBFC | 32 | Yes |
| INVESTIGATION_OFFICER | BANK, NBFC, AGENCY | 19 | Yes |
| COLLECTIONS_MANAGER | BANK, NBFC, AGENCY | 29 | Yes |
| FIELD_OFFICER | BANK, NBFC, AGENCY | 7 | No |
| AUDITOR | BANK, NBFC, COLLEGE | 18 | Yes |
| BORROWER | COLLEGE | 1 (`portal:self`) | Own loan only |

The full permission catalogue (58 permissions) and matrix are served by `GET /api/v1/admin/permissions` and shown
under Administration > Roles and permissions.

## Audit

Logins (success and failure), MFA, permission refusals, Student 360 access, data changes, approvals, exports
(with stated purpose), and grievance and case transitions are written to `audit_events`. Events are append-only,
hash-chained and protected by a trigger against modification by any role. Chain verification runs nightly and on
demand (`GET /api/v1/audit/verify`).

## Responsible-use safeguards (product boundary)

The product deliberately does **not** implement: coercive recovery, social-media scraping, covert or automatic
location capture (location capture disabled, OD-14), automated "absconding" or fraud labels, unauthorised
third-party contact (guarantor contact requires a recorded lawful basis), or automated adverse decisions. Risk
indicators use neutral wording, show their trigger data and rule version, and require a human decision with a
rationale before any case is created.

## Transport and headers

nginx sets `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` and hides
its version. TLS termination is a hosting decision (OD-19); all host ports bind to 127.0.0.1 in the reference
Compose file. `/metrics` (Prometheus) is served by the backend only and is not proxied by nginx.

## Verification

| Check | Evidence |
|---|---|
| Unprotected routes | B: test_foundation::test_every_route_declares_permission |
| Tenant isolation | B: test_foundation::test_rls_isolates_tenants, test_students::test_cross_tenant_user_cannot_see_demo |
| Cross-organization access | B: test_students::test_other_college_gets_404, test_loans::test_cross_bank_access_denied, test_cases::test_college_and_other_bank_cannot_read_anb_cases |
| Masking | B: test_loans::test_college_user_sees_no_financial_amounts, test_dashboard::test_dashboard_college_and_platform_have_no_financial_amounts; E: loans.spec (AC-02) |
| Borrower isolation | B: test_portal::test_borrower_cannot_reach_other_records; E: portal.spec, grievances.spec |
| Append-only / tamper | B: test_foundation::test_append_only_tables_reject_delete_by_app_role, ::test_audit_trigger_blocks_even_owner |
| Insecure production config | B: test_foundation::test_production_refuses_insecure_defaults |
| Secrets in repository | Manual scan on 2026-11-06 (see TESTING_AND_VALIDATION); gitleaks runs in CI |
