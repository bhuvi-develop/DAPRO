# DAPRO - Database Design

PostgreSQL 16 is the authoritative store. 50 tables, generated reference in
[`database/DATA_DICTIONARY.md`](database/DATA_DICTIONARY.md) (columns, types, keys, indexes, flags).

## Conventions

- Primary keys: UUIDv7 (time-ordered). Every tenant-owned table has `tenant_id`.
- Money: `NUMERIC(18,2)`, INR; serialized as decimal strings. Timestamps: `timestamptz` in UTC; business dates in
  Asia/Kolkata.
- Optimistic concurrency: `version` columns on mutable aggregates (students, cases, grievances, guarantors).
- History is appended, not overwritten: superseded addresses and employment records keep `is_current=false`
  and `superseded_at`; field corrections go to `student_field_changes` with old and new values.
- Data provenance: `source_type` / `source` columns (COLLEGE, BANK, BORROWER_REPORTED, STAFF, MOCK feed),
  `verification` status, and on loans `source_system`, `last_synced_at`, `sync_state` (CURRENT, STALE, FAILED, UNKNOWN).

## Domains

| Domain | Tables |
|---|---|
| Identity and access | tenants, organizations, org_units, sharing_agreements, users, roles, user_roles, user_sessions, user_invitations |
| Students | students, student_addresses, address_verifications, student_contacts, contact_preferences, consents, academic_records, employment_records, student_field_changes, duplicate_candidates, import_batches |
| Loans (bank mirror) | loan_accounts, loan_parties, guarantors, witnesses, repayment_schedules, schedule_instalments, repayment_transactions, loan_snapshots, reconciliation_items, mock_bank_records, integrations |
| Operations | risk_rules, risk_indicators, risk_reviews, cases, case_events, case_follow_ups, evidence, payment_commitments, field_visits |
| Engagement | notification_templates, communications, grievances, grievance_events, in_app_notifications |
| Platform | policy_configs, export_jobs, ref_counters, audit_events, audit_checkpoints |

## Security in the database (migration 0002)

- Two roles: the **owner** (`dapro_owner`) runs migrations and the seed; the application connects as
  **`dapro_app`** (`NOBYPASSRLS`).
- **Row-level security** on 42 tenant tables: policies compare `tenant_id` with `current_setting('app.tenant_id')`,
  which the API binds per transaction. Organization, branch and assignment scope are enforced in services.
- **Append-only** for `dapro_app`: audit_events, repayment_transactions, loan_snapshots, risk_reviews,
  student_field_changes, case_events, grievance_events (UPDATE/DELETE revoked).
- **Audit tamper trigger**: rejects UPDATE/DELETE on `audit_events` for every role, including the owner. Events are
  SHA-256 hash-chained per tenant; `audit_checkpoints` store nightly verification results.

## Migrations

| Revision | Content | Downgrade |
|---|---|---|
| 0001_initial_schema | All tables, keys, indexes, constraints | Drops the schema objects |
| 0002_security_rls | Application role, grants, RLS policies, append-only grants, audit trigger | Removes them |

Rules for the team:
1. Never edit a migration that may have been applied anywhere; add a new revision
   (`alembic revision -m "..."`), autogenerate only as a starting point and review it.
2. Every migration must downgrade cleanly. Check with `scripts/test-migrations.sh`
   (scratch database: upgrade head, downgrade base, upgrade head). It never touches the dev database.
3. Back up before migrating a shared database: `scripts/backup.sh`, rehearse with `scripts/restore-check.sh`.

## Data sources and demo data

Every row in the demo environment belongs to the `DEMO` tenant and is synthetic. Bank data comes from the
`mock_bank_records` table through the MOCK adapter and is labelled MOCK in API freshness blocks and in the UI.
There is no REAL or IMPORTED bank data in this build; the source labels exist so that a live adapter's data
will stay distinguishable (OD-06).
