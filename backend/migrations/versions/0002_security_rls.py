"""Security layer: application role, row-level security, append-only grants, audit tamper trigger.

Revision ID: 0002
Revises: 0001
Rollback: alembic downgrade 0001  (drops policies, trigger and grants; the dapro_app role is kept if it owns
nothing else, so a re-upgrade is safe). No business data is touched in either direction.
"""
import os

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

RLS_TABLES = [
    "academic_records", "address_verifications", "audit_checkpoints", "audit_events", "case_events",
    "case_follow_ups", "cases", "communications", "consents", "contact_preferences", "duplicate_candidates",
    "employment_records", "evidence", "export_jobs", "field_visits", "grievance_events", "grievances",
    "guarantors", "import_batches", "in_app_notifications", "integrations", "loan_accounts", "loan_parties",
    "loan_snapshots", "mock_bank_records", "notification_templates", "payment_commitments", "policy_configs",
    "reconciliation_items", "ref_counters", "repayment_schedules", "repayment_transactions", "risk_indicators",
    "risk_reviews", "risk_rules", "schedule_instalments", "sharing_agreements", "student_addresses",
    "student_contacts", "student_field_changes", "students", "witnesses",
]

# Append-only from the application's point of view (FR-REP-05, FR-RSK-06, FR-AUD-03, LLD section 2).
APPEND_ONLY = ["audit_events", "repayment_transactions", "loan_snapshots", "risk_reviews", "student_field_changes",
               "case_events", "grievance_events"]


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    password = os.environ.get("DAPRO_APP_DB_PASSWORD", "dapro_app")
    op.execute(f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dapro_app') THEN
            CREATE ROLE dapro_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD {_quote(password)};
          ELSE
            BEGIN
              ALTER ROLE dapro_app WITH LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD {_quote(password)};
            EXCEPTION WHEN OTHERS THEN
              -- roles are cluster-wide: a concurrent migration on another database may hold the row
              RAISE NOTICE 'dapro_app role update skipped: %', SQLERRM;
            END;
          END IF;
        END $$;
    """)
    op.execute("GRANT USAGE ON SCHEMA public TO dapro_app")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO dapro_app")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO dapro_app")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO dapro_app")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO dapro_app")
    op.execute("REVOKE ALL ON alembic_version FROM dapro_app")

    for table in APPEND_ONLY:
        op.execute(f"REVOKE UPDATE, DELETE ON {table} FROM dapro_app")

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
        """)

    # Tamper resistance: audit rows cannot be changed or deleted by ANY role while the trigger exists.
    op.execute("""
        CREATE OR REPLACE FUNCTION dapro_block_audit_mutation() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'audit_events is append-only (FR-AUD-03): % blocked', TG_OP
            USING ERRCODE = 'insufficient_privilege';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION dapro_block_audit_mutation()
    """)
    op.execute("""
        CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION dapro_block_audit_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS dapro_block_audit_mutation()")
    for table in RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM dapro_app")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM dapro_app")
