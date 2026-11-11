# DAPRO - Data Dictionary

Generated from SQLAlchemy metadata (`backend/scripts/gen_docs.py`). Identifiers are UUIDv7. Money is NUMERIC(18,2) INR. Timestamps are UTC (timestamptz).

Legend: RLS = row-level security tenant isolation; APPEND-ONLY = UPDATE/DELETE revoked from dapro_app (audit_events additionally protected by a trigger for every role).

## academic_records  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| college_org_id | UUID | no | FK organizations.id |
| programme | TEXT | no |  |
| course | TEXT | no |  |
| specialization | TEXT | yes |  |
| cohort_year | INTEGER | no |  |
| enrolment_status | VARCHAR(20) | no |  |
| start_date | DATE | yes |  |
| expected_completion | DATE | yes |  |
| actual_completion | DATE | yes |  |
| source | VARCHAR(30) | no | default COLLEGE_PROVIDED |
| verification | VARCHAR(20) | no | default VERIFIED |
| is_current | BOOLEAN | no |  |
| superseded_at | DATETIME | yes |  |
| recorded_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_academic_records_college_org_id, ix_academic_records_student_id, ix_academic_records_tenant_id

## address_verifications  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| address_id | UUID | no | FK student_addresses.id |
| student_id | UUID | no | FK students.id |
| method | VARCHAR(30) | no |  |
| status | VARCHAR(20) | no | default PENDING |
| requested_by | UUID | yes |  |
| assigned_to | UUID | yes |  |
| outcome_notes | TEXT | yes |  |
| performed_by | UUID | yes |  |
| performed_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_address_verifications_address_id, ix_address_verifications_status, ix_address_verifications_student_id, ix_address_verifications_tenant_id

## audit_checkpoints  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| verified_at | DATETIME | no | default now() |
| last_seq | BIGINT | no |  |
| last_hash | TEXT | yes |  |
| events_checked | INTEGER | no |  |
| ok | BOOLEAN | no |  |
| error | TEXT | yes |  |
| triggered_by | VARCHAR(20) | no | default SCHEDULE |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_audit_checkpoints_tenant_id

## audit_events  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| seq | BIGINT | no | PK, default  |
| id | UUID | no |  |
| tenant_id | UUID | no |  |
| occurred_at | DATETIME | no |  |
| actor_id | UUID | yes |  |
| actor_label | TEXT | yes |  |
| actor_role | VARCHAR(40) | yes |  |
| org_id | UUID | yes |  |
| action | VARCHAR(80) | no |  |
| target_type | VARCHAR(40) | yes |  |
| target_id | VARCHAR(80) | yes |  |
| target_label | TEXT | yes |  |
| outcome | VARCHAR(20) | no |  |
| purpose | VARCHAR(40) | yes |  |
| correlation_id | VARCHAR(64) | no |  |
| ip | TEXT | yes |  |
| payload | JSONB | no |  |
| prev_hash | VARCHAR(64) | no |  |
| hash | VARCHAR(64) | no |  |

Unique: (id)
Indexes: ix_audit_events_action, ix_audit_events_occurred_at, ix_audit_events_org_id, ix_audit_events_target_id, ix_audit_events_target_type, ix_audit_events_tenant_id

## case_events  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| case_id | UUID | no | FK cases.id |
| event_type | VARCHAR(40) | no |  |
| from_status | VARCHAR(30) | yes |  |
| to_status | VARCHAR(30) | yes |  |
| summary | TEXT | no |  |
| data | JSONB | no | default {} |
| actor_id | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_case_events_case_id, ix_case_events_tenant_id

## case_follow_ups  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| case_id | UUID | no | FK cases.id |
| channel | VARCHAR(20) | no |  |
| outcome | VARCHAR(40) | no |  |
| notes | TEXT | no |  |
| contacted_at | DATETIME | no |  |
| next_follow_up_on | DATE | yes |  |
| actor_id | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_case_follow_ups_case_id, ix_case_follow_ups_tenant_id

## cases  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| case_ref | VARCHAR(30) | no |  |
| student_id | UUID | no | FK students.id |
| loan_id | UUID | yes | FK loan_accounts.id |
| bank_org_id | UUID | yes | FK organizations.id |
| college_org_id | UUID | yes | FK organizations.id |
| category | VARCHAR(40) | no |  |
| reason | TEXT | no |  |
| source | VARCHAR(30) | no | default MANUAL |
| source_ref | TEXT | yes |  |
| priority | VARCHAR(10) | no | default MEDIUM |
| status | VARCHAR(30) | no | default NEW |
| previous_status | VARCHAR(30) | yes |  |
| owner_id | UUID | yes | FK users.id |
| team_unit_id | UUID | yes | FK org_units.id |
| next_action | TEXT | yes |  |
| due_on | DATE | yes |  |
| opened_by | UUID | yes |  |
| resolution_type | VARCHAR(40) | yes |  |
| resolution_notes | TEXT | yes |  |
| resolution_evidence | JSONB | yes |  |
| resolved_at | DATETIME | yes |  |
| closed_at | DATETIME | yes |  |
| closed_by | UUID | yes |  |
| version | INTEGER | no |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, case_ref)
Indexes: ix_cases_bank_org_id, ix_cases_category, ix_cases_college_org_id, ix_cases_due_on, ix_cases_loan_id, ix_cases_owner_id, ix_cases_priority, ix_cases_status, ix_cases_student_id, ix_cases_team_unit_id, ix_cases_tenant_id

## communications  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| case_id | UUID | yes | FK cases.id |
| guarantor_id | UUID | yes | FK guarantors.id |
| recipient_type | VARCHAR(20) | no | default BORROWER |
| template_id | UUID | yes |  |
| template_code | TEXT | yes |  |
| template_version | INTEGER | yes |  |
| channel | VARCHAR(10) | no |  |
| recipient_masked | TEXT | yes |  |
| purpose | VARCHAR(30) | no |  |
| status | VARCHAR(20) | no | default QUEUED |
| block_reason | TEXT | yes |  |
| provider | TEXT | yes |  |
| provider_mode | VARCHAR(20) | no | default MOCK |
| provider_message_id | TEXT | yes |  |
| error | TEXT | yes |  |
| rendered_subject | TEXT | yes |  |
| rendered_body | TEXT | yes |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| sent_at | DATETIME | yes |  |
| delivered_at | DATETIME | yes |  |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_communications_case_id, ix_communications_guarantor_id, ix_communications_status, ix_communications_student_id, ix_communications_tenant_id

## consents  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| basis | VARCHAR(30) | no |  |
| purposes | ARRAY | no | default {} |
| notice_version | VARCHAR(30) | no |  |
| source | VARCHAR(30) | no |  |
| valid_from | DATETIME | no |  |
| valid_to | DATETIME | yes |  |
| withdrawn_at | DATETIME | yes |  |
| recorded_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_consents_student_id, ix_consents_tenant_id

## contact_preferences  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| channel | VARCHAR(10) | no |  |
| allowed | BOOLEAN | no |  |
| quiet_start | TIME | no |  |
| quiet_end | TIME | no |  |
| timezone | VARCHAR(40) | no | default Asia/Kolkata |
| language | VARCHAR(10) | no | default en |
| updated_by | UUID | yes |  |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (student_id, channel)
Indexes: ix_contact_preferences_student_id, ix_contact_preferences_tenant_id

## duplicate_candidates  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| candidate_student_id | UUID | no | FK students.id |
| match_fields | ARRAY | no | default {} |
| score | INTEGER | no |  |
| status | VARCHAR(30) | no | default OPEN |
| reviewed_by | UUID | yes |  |
| reviewed_at | DATETIME | yes |  |
| notes | TEXT | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_duplicate_candidates_candidate_student_id, ix_duplicate_candidates_status, ix_duplicate_candidates_student_id, ix_duplicate_candidates_tenant_id

## employment_records  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| status | VARCHAR(20) | no |  |
| employer_name | TEXT | yes |  |
| job_title | TEXT | yes |  |
| sector | TEXT | yes |  |
| city | TEXT | yes |  |
| country | VARCHAR(2) | yes |  |
| source | VARCHAR(30) | no |  |
| verification | VARCHAR(20) | no | default UNVERIFIED |
| verified_by | UUID | yes |  |
| verified_at | DATETIME | yes |  |
| reported_on | DATE | no |  |
| effective_from | DATE | yes |  |
| is_current | BOOLEAN | no |  |
| superseded_at | DATETIME | yes |  |
| notes | TEXT | yes |  |
| recorded_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_employment_records_student_id, ix_employment_records_tenant_id

## evidence  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| case_id | UUID | no | FK cases.id |
| visit_id | UUID | yes |  |
| kind | VARCHAR(30) | no |  |
| title | TEXT | no |  |
| description | TEXT | yes |  |
| file_name | TEXT | yes |  |
| mime_type | TEXT | yes |  |
| size_bytes | INTEGER | yes |  |
| sha256 | VARCHAR(64) | yes |  |
| storage_key | TEXT | yes |  |
| classification | VARCHAR(20) | no | default RESTRICTED |
| evidence_quality | VARCHAR(30) | no | default OFFICER_OBSERVATION |
| uploaded_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_evidence_case_id, ix_evidence_tenant_id

## export_jobs  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| report_code | VARCHAR(40) | no |  |
| title | TEXT | no |  |
| filters | JSONB | no |  |
| purpose | TEXT | no |  |
| format | VARCHAR(10) | no | default CSV |
| status | VARCHAR(20) | no | default QUEUED |
| row_count | INTEGER | yes |  |
| file_name | TEXT | yes |  |
| sha256 | VARCHAR(64) | yes |  |
| storage_key | TEXT | yes |  |
| as_of | DATETIME | yes |  |
| error | TEXT | yes |  |
| requested_by | UUID | no |  |
| completed_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_export_jobs_report_code, ix_export_jobs_tenant_id

## field_visits  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| case_id | UUID | no | FK cases.id |
| officer_id | UUID | no | FK users.id |
| status | VARCHAR(20) | no | default SCHEDULED |
| purpose | TEXT | no |  |
| scheduled_for | DATETIME | yes |  |
| check_in_at | DATETIME | yes |  |
| check_out_at | DATETIME | yes |  |
| visited_at | DATETIME | yes |  |
| outcome | VARCHAR(30) | yes |  |
| address_id | UUID | yes |  |
| notes | TEXT | yes |  |
| borrower_present | BOOLEAN | yes |  |
| safety_incident | BOOLEAN | no |  |
| incident_notes | TEXT | yes |  |
| location_captured | BOOLEAN | no |  |
| review_status | VARCHAR(20) | no | default NOT_REQUIRED |
| reviewer_id | UUID | yes |  |
| reviewed_at | DATETIME | yes |  |
| review_notes | TEXT | yes |  |
| client_draft_id | VARCHAR(64) | yes |  |
| version | INTEGER | no |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, client_draft_id)
Indexes: ix_field_visits_case_id, ix_field_visits_officer_id, ix_field_visits_review_status, ix_field_visits_status, ix_field_visits_tenant_id

## grievance_events  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| grievance_id | UUID | no | FK grievances.id |
| event_type | VARCHAR(30) | no |  |
| visibility | VARCHAR(20) | no | default BORROWER |
| message | TEXT | no |  |
| from_status | VARCHAR(30) | yes |  |
| to_status | VARCHAR(30) | yes |  |
| actor_id | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_grievance_events_grievance_id, ix_grievance_events_tenant_id

## grievances  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| ref | VARCHAR(30) | no |  |
| student_id | UUID | no | FK students.id |
| loan_id | UUID | yes | FK loan_accounts.id |
| case_id | UUID | yes | FK cases.id |
| category | VARCHAR(30) | no |  |
| subject | TEXT | no |  |
| description | TEXT | no |  |
| channel | VARCHAR(20) | no |  |
| submitted_by_user_id | UUID | yes |  |
| subject_user_id | UUID | yes |  |
| owner_id | UUID | yes | FK users.id |
| owning_org_id | UUID | yes | FK organizations.id |
| status | VARCHAR(30) | no | default SUBMITTED |
| priority | VARCHAR(10) | no | default MEDIUM |
| due_on | DATE | yes |  |
| correction_field | TEXT | yes |  |
| correction_requested_value | TEXT | yes |  |
| resolution | TEXT | yes |  |
| resolved_at | DATETIME | yes |  |
| closed_at | DATETIME | yes |  |
| version | INTEGER | no |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, ref)
Indexes: ix_grievances_case_id, ix_grievances_category, ix_grievances_loan_id, ix_grievances_owner_id, ix_grievances_owning_org_id, ix_grievances_status, ix_grievances_student_id, ix_grievances_tenant_id

## guarantors  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| loan_id | UUID | no | FK loan_accounts.id |
| full_name | TEXT | no |  |
| relationship_to_borrower | TEXT | yes |  |
| mobile | TEXT | yes |  |
| email | TEXT | yes |  |
| address_text | TEXT | yes |  |
| city | TEXT | yes |  |
| state | TEXT | yes |  |
| agreement_ref | TEXT | no |  |
| agreement_executed_on | DATE | yes |  |
| guarantee_scope | TEXT | yes |  |
| guarantee_status | VARCHAR(20) | no | default ACTIVE |
| verification | VARCHAR(20) | no | default UNVERIFIED |
| verified_by | UUID | yes |  |
| verified_at | DATETIME | yes |  |
| communication_permitted | BOOLEAN | no |  |
| communication_basis | TEXT | yes |  |
| source | VARCHAR(30) | no | default BANK_PROVIDED |
| approval_status | VARCHAR(20) | no | default APPROVED |
| pending_change | JSONB | yes |  |
| pending_by | UUID | yes |  |
| approved_by | UUID | yes |  |
| version | INTEGER | no |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_guarantors_loan_id, ix_guarantors_tenant_id

## import_batches  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| org_id | UUID | no | FK organizations.id |
| kind | VARCHAR(30) | no |  |
| source | VARCHAR(30) | no |  |
| file_name | TEXT | yes |  |
| checksum | VARCHAR(64) | yes |  |
| status | VARCHAR(20) | no | default QUEUED |
| total_rows | INTEGER | no |  |
| valid_rows | INTEGER | no |  |
| applied_rows | INTEGER | no |  |
| error_rows | INTEGER | no |  |
| duplicate_rows | INTEGER | no |  |
| errors | JSONB | no | default [] |
| summary | JSONB | no | default {} |
| storage_key | TEXT | yes |  |
| requires_approval | BOOLEAN | no |  |
| uploaded_by | UUID | yes |  |
| approved_by | UUID | yes |  |
| approved_at | DATETIME | yes |  |
| correlation_id | TEXT | yes |  |
| data_origin | VARCHAR(10) | no | default LIVE |
| started_at | DATETIME | yes |  |
| finished_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_import_batches_checksum, ix_import_batches_org_id, ix_import_batches_status, ix_import_batches_tenant_id

## in_app_notifications  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| user_id | UUID | no | FK users.id |
| kind | VARCHAR(40) | no |  |
| title | TEXT | no |  |
| body | TEXT | yes |  |
| link | TEXT | yes |  |
| severity | VARCHAR(10) | no | default INFO |
| read_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_in_app_notifications_tenant_id, ix_in_app_notifications_user_id

## integrations  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| org_id | UUID | yes | FK organizations.id |
| kind | VARCHAR(30) | no |  |
| name | TEXT | no |  |
| provider | TEXT | no |  |
| mode | VARCHAR(20) | no |  |
| health | VARCHAR(20) | no | default UNKNOWN |
| last_success_at | DATETIME | yes |  |
| last_failure_at | DATETIME | yes |  |
| last_error | TEXT | yes |  |
| consecutive_failures | INTEGER | no |  |
| refresh_interval_hours | INTEGER | no |  |
| simulate_failure | BOOLEAN | no |  |
| config | JSONB | no | default {} |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_integrations_org_id, ix_integrations_tenant_id

## loan_accounts  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| bank_org_id | UUID | no | FK organizations.id |
| branch_unit_id | UUID | yes | FK org_units.id |
| student_id | UUID | yes | FK students.id |
| college_org_id | UUID | yes | FK organizations.id |
| bank_loan_ref | VARCHAR(60) | no |  |
| bank_borrower_ref | TEXT | yes |  |
| product_name | TEXT | yes |  |
| scheme | TEXT | yes |  |
| bank_status | VARCHAR(20) | no | default UNKNOWN |
| sanctioned_amount | NUMERIC(18, 2) | yes |  |
| disbursed_amount | NUMERIC(18, 2) | yes |  |
| sanction_date | DATE | yes |  |
| first_disbursement_date | DATE | yes |  |
| moratorium_end | DATE | yes |  |
| repayment_start | DATE | yes |  |
| tenure_months | INTEGER | yes |  |
| interest_rate_pct | NUMERIC(18, 2) | yes |  |
| emi_amount | NUMERIC(18, 2) | yes |  |
| currency | VARCHAR(3) | no | default INR |
| link_status | VARCHAR(20) | no | default PENDING_REVIEW |
| link_validation | JSONB | no | default {} |
| linked_by | UUID | yes |  |
| linked_at | DATETIME | yes |  |
| sync_state | VARCHAR(20) | no | default UNKNOWN |
| last_synced_at | DATETIME | yes |  |
| last_sync_batch_id | UUID | yes |  |
| source_system | VARCHAR(40) | no | default MOCK_BANK_FEED |
| source_record_id | TEXT | yes |  |
| data_origin | VARCHAR(10) | no | default LIVE |
| repayment_status | VARCHAR(20) | no | default UNKNOWN |
| dpd | INTEGER | yes |  |
| dpd_bucket | VARCHAR(20) | yes |  |
| overdue_amount | NUMERIC(18, 2) | yes |  |
| principal_outstanding | NUMERIC(18, 2) | yes |  |
| next_due_date | DATE | yes |  |
| next_due_amount | NUMERIC(18, 2) | yes |  |
| status_evaluated_at | DATETIME | yes |  |
| version | INTEGER | no |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, bank_org_id, bank_loan_ref)
Indexes: ix_loan_accounts_bank_loan_ref, ix_loan_accounts_bank_org_id, ix_loan_accounts_branch_unit_id, ix_loan_accounts_college_org_id, ix_loan_accounts_dpd_bucket, ix_loan_accounts_link_status, ix_loan_accounts_repayment_status, ix_loan_accounts_student_id, ix_loan_accounts_sync_state, ix_loan_accounts_tenant_id

## loan_parties  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| loan_id | UUID | no | FK loan_accounts.id |
| student_id | UUID | yes | FK students.id |
| party_role | VARCHAR(20) | no |  |
| full_name | TEXT | no |  |
| relationship | TEXT | yes |  |
| source | VARCHAR(30) | no | default BANK_PROVIDED |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_loan_parties_loan_id, ix_loan_parties_student_id, ix_loan_parties_tenant_id

## loan_snapshots  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| loan_id | UUID | no | FK loan_accounts.id |
| as_of | DATETIME | no |  |
| principal_outstanding | NUMERIC(18, 2) | yes |  |
| interest_charges | NUMERIC(18, 2) | yes |  |
| overdue_amount | NUMERIC(18, 2) | yes |  |
| total_due | NUMERIC(18, 2) | yes |  |
| bank_dpd | INTEGER | yes |  |
| bank_status | VARCHAR(20) | yes |  |
| source_system | VARCHAR(40) | no |  |
| source_batch_id | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_loan_snapshots_loan_id, ix_loan_snapshots_tenant_id

## mock_bank_records  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| bank_org_id | UUID | no | FK organizations.id |
| branch_code | TEXT | yes |  |
| bank_loan_ref | VARCHAR(60) | no |  |
| bank_borrower_ref | TEXT | no |  |
| borrower_name | TEXT | no |  |
| borrower_dob | DATE | yes |  |
| terms | JSONB | no |  |
| profile | VARCHAR(20) | no |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, bank_org_id, bank_loan_ref)
Indexes: ix_mock_bank_records_bank_org_id, ix_mock_bank_records_tenant_id

## notification_templates  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| org_id | UUID | yes | FK organizations.id |
| code | VARCHAR(60) | no |  |
| version | INTEGER | no |  |
| name | TEXT | no |  |
| channel | VARCHAR(10) | no |  |
| purpose | VARCHAR(30) | no |  |
| language | VARCHAR(10) | no | default en |
| subject | TEXT | yes |  |
| body | TEXT | no |  |
| status | VARCHAR(20) | no | default DRAFT |
| approval_label | VARCHAR(30) | no | default DEMO_FIXTURE |
| created_by | UUID | yes |  |
| approved_by | UUID | yes |  |
| approved_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, code, version)
Indexes: ix_notification_templates_org_id, ix_notification_templates_tenant_id

## org_units

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| org_id | UUID | no | FK organizations.id |
| parent_id | UUID | yes | FK org_units.id |
| kind | VARCHAR(20) | no |  |
| code | VARCHAR(40) | no |  |
| name | TEXT | no |  |
| city | TEXT | yes |  |
| state | TEXT | yes |  |
| status | VARCHAR(20) | no | default ACTIVE |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (org_id, code)
Indexes: ix_org_units_org_id, ix_org_units_parent_id, ix_org_units_tenant_id

## organizations

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| type | VARCHAR(20) | no |  |
| code | VARCHAR(40) | no |  |
| name | TEXT | no |  |
| legal_name | TEXT | yes |  |
| status | VARCHAR(20) | no | default ACTIVE |
| city | TEXT | yes |  |
| state | TEXT | yes |  |
| contact_email | TEXT | yes |  |
| settings | JSONB | no | default {} |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, code)
Indexes: ix_organizations_tenant_id

## payment_commitments  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| case_id | UUID | no | FK cases.id |
| loan_id | UUID | yes | FK loan_accounts.id |
| visit_id | UUID | yes |  |
| amount | NUMERIC(18, 2) | no |  |
| promised_date | DATE | no |  |
| source | VARCHAR(30) | no | default BORROWER_REPORTED |
| status | VARCHAR(20) | no | default OPEN |
| bank_txn_ref | TEXT | yes |  |
| notes | TEXT | yes |  |
| recorded_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_payment_commitments_case_id, ix_payment_commitments_loan_id, ix_payment_commitments_tenant_id

## policy_configs  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| key | VARCHAR(60) | no |  |
| version | INTEGER | no |  |
| value | JSONB | no |  |
| status | VARCHAR(20) | no | default ACTIVE |
| approval_label | VARCHAR(30) | no | default DEMO_FIXTURE |
| description | TEXT | no |  |
| effective_from | DATE | no |  |
| created_by | UUID | yes |  |
| approved_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, key, version)
Indexes: ix_policy_configs_tenant_id

## reconciliation_items  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| bank_org_id | UUID | yes | FK organizations.id |
| loan_id | UUID | yes | FK loan_accounts.id |
| student_id | UUID | yes | FK students.id |
| batch_id | UUID | yes |  |
| kind | VARCHAR(30) | no |  |
| severity | VARCHAR(10) | no | default MEDIUM |
| summary | TEXT | no |  |
| details | JSONB | no | default {} |
| status | VARCHAR(20) | no | default OPEN |
| resolution | TEXT | yes |  |
| resolved_by | UUID | yes |  |
| resolved_at | DATETIME | yes |  |
| dedupe_key | VARCHAR(200) | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_reconciliation_items_bank_org_id, ix_reconciliation_items_dedupe_key, ix_reconciliation_items_kind, ix_reconciliation_items_loan_id, ix_reconciliation_items_status, ix_reconciliation_items_student_id, ix_reconciliation_items_tenant_id

## ref_counters  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| name | VARCHAR(40) | no |  |
| value | BIGINT | no |  |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, name)
Indexes: ix_ref_counters_tenant_id

## repayment_schedules  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| loan_id | UUID | no | FK loan_accounts.id |
| version | INTEGER | no |  |
| schedule_ref | TEXT | no |  |
| reason | VARCHAR(20) | no | default ORIGINAL |
| effective_from | DATE | no |  |
| is_current | BOOLEAN | no |  |
| source_system | VARCHAR(40) | no |  |
| source_batch_id | UUID | yes |  |
| received_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (loan_id, version)
Indexes: ix_repayment_schedules_loan_id, ix_repayment_schedules_tenant_id

## repayment_transactions  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| loan_id | UUID | no | FK loan_accounts.id |
| bank_txn_ref | VARCHAR(80) | no |  |
| posted_on | DATE | no |  |
| value_on | DATE | yes |  |
| amount | NUMERIC(18, 2) | no |  |
| kind | VARCHAR(20) | no |  |
| channel | VARCHAR(30) | yes |  |
| payment_reference | TEXT | yes |  |
| reverses_txn_ref | TEXT | yes |  |
| allocations | JSONB | no | default [] |
| source_system | VARCHAR(40) | no |  |
| source_batch_id | UUID | yes |  |
| received_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, bank_txn_ref)
Indexes: ix_repayment_transactions_loan_id, ix_repayment_transactions_posted_on, ix_repayment_transactions_tenant_id

## risk_indicators  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| loan_id | UUID | yes | FK loan_accounts.id |
| bank_org_id | UUID | yes | FK organizations.id |
| rule_id | UUID | no | FK risk_rules.id |
| rule_code | VARCHAR(40) | no |  |
| rule_version | INTEGER | no |  |
| category | VARCHAR(40) | no |  |
| severity | VARCHAR(20) | no |  |
| title | TEXT | no |  |
| explanation | TEXT | no |  |
| evidence | JSONB | no |  |
| input_snapshot | JSONB | no |  |
| status | VARCHAR(20) | no | default OPEN |
| assigned_to | UUID | yes |  |
| case_id | UUID | yes |  |
| dedupe_key | VARCHAR(200) | no |  |
| generated_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_risk_indicators_bank_org_id, ix_risk_indicators_category, ix_risk_indicators_dedupe_key, ix_risk_indicators_loan_id, ix_risk_indicators_rule_code, ix_risk_indicators_rule_id, ix_risk_indicators_severity, ix_risk_indicators_status, ix_risk_indicators_student_id, ix_risk_indicators_tenant_id

## risk_reviews  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| indicator_id | UUID | no | FK risk_indicators.id |
| reviewer_id | UUID | no |  |
| decision | VARCHAR(30) | no |  |
| rationale | TEXT | no |  |
| override_severity | VARCHAR(20) | yes |  |
| evidence_ref | TEXT | yes |  |
| case_id | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_risk_reviews_indicator_id, ix_risk_reviews_tenant_id

## risk_rules  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| code | VARCHAR(40) | no |  |
| version | INTEGER | no |  |
| name | TEXT | no |  |
| category | VARCHAR(40) | no |  |
| description | TEXT | no |  |
| params | JSONB | no |  |
| severity | VARCHAR(20) | no |  |
| recommended_action | TEXT | no |  |
| status | VARCHAR(20) | no | default DRAFT |
| approval_label | VARCHAR(30) | no | default DEMO_FIXTURE |
| effective_from | DATE | yes |  |
| change_reason | TEXT | yes |  |
| created_by | UUID | yes |  |
| approved_by | UUID | yes |  |
| approved_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, code, version)
Indexes: ix_risk_rules_tenant_id

## roles

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| code | VARCHAR(40) | no |  |
| name | TEXT | no |  |
| description | TEXT | yes |  |
| org_types | ARRAY | no | default {} |
| permissions | ARRAY | no | default {} |
| is_system | BOOLEAN | no |  |
| version | INTEGER | no |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, code)
Indexes: ix_roles_tenant_id

## schedule_instalments  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| schedule_id | UUID | no | FK repayment_schedules.id |
| loan_id | UUID | no | FK loan_accounts.id |
| instalment_no | INTEGER | no |  |
| due_date | DATE | no |  |
| amount_due | NUMERIC(18, 2) | no |  |
| principal_component | NUMERIC(18, 2) | yes |  |
| interest_component | NUMERIC(18, 2) | yes |  |
| bank_allocated_amount | NUMERIC(18, 2) | yes |  |
| bank_status | VARCHAR(20) | yes |  |
| status | VARCHAR(20) | no | default UNKNOWN |
| dpd | INTEGER | yes |  |
| evaluated_at | DATETIME | yes |  |
| tenant_id | UUID | no | FK tenants.id |

Unique: (schedule_id, instalment_no)
Indexes: ix_schedule_instalments_due_date, ix_schedule_instalments_loan_id, ix_schedule_instalments_schedule_id, ix_schedule_instalments_status, ix_schedule_instalments_tenant_id

## sharing_agreements  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| reference | TEXT | no |  |
| college_org_id | UUID | no | FK organizations.id |
| bank_org_id | UUID | no | FK organizations.id |
| purposes | ARRAY | no | default {} |
| shared_fields | ARRAY | no | default {} |
| status | VARCHAR(20) | no | default ACTIVE |
| effective_from | DATE | no |  |
| effective_to | DATE | yes |  |
| approval_label | VARCHAR(30) | no | default DEMO_FIXTURE |
| notes | TEXT | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_sharing_agreements_bank_org_id, ix_sharing_agreements_college_org_id, ix_sharing_agreements_tenant_id

## student_addresses  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| kind | VARCHAR(20) | no |  |
| line1 | TEXT | no |  |
| line2 | TEXT | yes |  |
| city | TEXT | no |  |
| district | TEXT | yes |  |
| state | TEXT | yes |  |
| postal_code | VARCHAR(12) | yes |  |
| country | VARCHAR(2) | no | default IN |
| source_type | VARCHAR(30) | no |  |
| source_ref | TEXT | yes |  |
| verification | VARCHAR(20) | no | default UNVERIFIED |
| verification_method | VARCHAR(30) | yes |  |
| verified_by | UUID | yes |  |
| verified_at | DATETIME | yes |  |
| effective_from | DATE | yes |  |
| is_current | BOOLEAN | no |  |
| superseded_at | DATETIME | yes |  |
| superseded_by_id | UUID | yes |  |
| notes | TEXT | yes |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_student_addresses_student_id, ix_student_addresses_tenant_id, ix_student_addresses_verification

## student_contacts  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| kind | VARCHAR(20) | no |  |
| value | TEXT | no |  |
| is_primary | BOOLEAN | no |  |
| source | VARCHAR(30) | no |  |
| verification | VARCHAR(20) | no | default UNVERIFIED |
| effective_from | DATE | yes |  |
| superseded_at | DATETIME | yes |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_student_contacts_student_id, ix_student_contacts_tenant_id

## student_field_changes  `RLS APPEND-ONLY`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| student_id | UUID | no | FK students.id |
| field | VARCHAR(60) | no |  |
| old_value | TEXT | yes |  |
| new_value | TEXT | yes |  |
| reason | TEXT | no |  |
| source | VARCHAR(30) | no | default STAFF_ENTERED |
| actor_id | UUID | yes |  |
| approved_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_student_field_changes_student_id, ix_student_field_changes_tenant_id

## students  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| dapro_ref | VARCHAR(30) | no |  |
| college_org_id | UUID | no | FK organizations.id |
| campus_unit_id | UUID | yes | FK org_units.id |
| college_student_id | VARCHAR(60) | no |  |
| first_name | TEXT | no |  |
| last_name | TEXT | no |  |
| full_name | TEXT | no |  |
| name_norm | TEXT | no |  |
| dob | DATE | yes |  |
| gender | VARCHAR(20) | yes |  |
| kyc_ref_last4 | VARCHAR(4) | yes |  |
| nationality | VARCHAR(2) | no | default IN |
| primary_email | TEXT | yes |  |
| primary_mobile | TEXT | yes |  |
| lifecycle_status | VARCHAR(20) | no | default STUDYING |
| record_status | VARCHAR(20) | no | default ACTIVE |
| verification_status | VARCHAR(20) | no | default UNVERIFIED |
| source | VARCHAR(30) | no | default STAFF_ENTERED |
| source_ref | TEXT | yes |  |
| import_batch_id | UUID | yes |  |
| profile_completion | INTEGER | no |  |
| data_origin | VARCHAR(10) | no | default LIVE |
| merged_into_id | UUID | yes |  |
| version | INTEGER | no |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, college_org_id, college_student_id); (tenant_id, dapro_ref)
Indexes: ix_students_campus_unit_id, ix_students_college_org_id, ix_students_full_name, ix_students_lifecycle_status, ix_students_name_norm, ix_students_tenant_id

## tenants

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| code | VARCHAR(40) | no |  |
| name | TEXT | no |  |
| status | VARCHAR(20) | no | default ACTIVE |
| environment_label | VARCHAR(20) | no | default DEMO |
| created_at | DATETIME | no | default now() |

Unique: (code)

## user_invitations

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| user_id | UUID | no | FK users.id |
| token_hash | VARCHAR(64) | no |  |
| expires_at | DATETIME | no |  |
| accepted_at | DATETIME | yes |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (token_hash)
Indexes: ix_user_invitations_tenant_id, ix_user_invitations_user_id

## user_roles

| Column | Type | Null | Key / default |
|---|---|---|---|
| user_id | UUID | no | PK, FK users.id |
| role_id | UUID | no | PK, FK roles.id |

## user_sessions

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| user_id | UUID | no | FK users.id |
| refresh_hash | VARCHAR(64) | no |  |
| ip | TEXT | yes |  |
| user_agent | TEXT | yes |  |
| mfa_passed | BOOLEAN | no |  |
| created_at | DATETIME | no | default now() |
| last_seen_at | DATETIME | no |  |
| expires_at | DATETIME | no |  |
| revoked_at | DATETIME | yes |  |
| revoked_reason | TEXT | yes |  |
| tenant_id | UUID | no | FK tenants.id |

Unique: (refresh_hash)
Indexes: ix_user_sessions_tenant_id, ix_user_sessions_user_id

## users

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| org_id | UUID | no | FK organizations.id |
| org_unit_id | UUID | yes | FK org_units.id |
| student_id | UUID | yes | FK students.id |
| email | VARCHAR(254) | no |  |
| full_name | TEXT | no |  |
| title | TEXT | yes |  |
| phone | TEXT | yes |  |
| password_hash | TEXT | yes |  |
| status | VARCHAR(20) | no | default INVITED |
| mfa_enabled | BOOLEAN | no |  |
| mfa_secret | TEXT | yes |  |
| failed_logins | INTEGER | no |  |
| locked_until | DATETIME | yes |  |
| last_login_at | DATETIME | yes |  |
| timezone | VARCHAR(40) | no | default Asia/Kolkata |
| created_by | UUID | yes |  |
| activated_at | DATETIME | yes |  |
| created_at | DATETIME | no | default now() |
| updated_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |

Unique: (tenant_id, email)
Indexes: ix_users_email, ix_users_org_id, ix_users_org_unit_id, ix_users_student_id, ix_users_tenant_id

## witnesses  `RLS`

| Column | Type | Null | Key / default |
|---|---|---|---|
| id | UUID | no | PK |
| loan_id | UUID | no | FK loan_accounts.id |
| full_name | TEXT | no |  |
| document_ref | TEXT | no |  |
| witnessed_on | DATE | yes |  |
| address_city | TEXT | yes |  |
| source | VARCHAR(30) | no | default BANK_PROVIDED |
| verification | VARCHAR(20) | no | default UNVERIFIED |
| notes | TEXT | yes |  |
| created_by | UUID | yes |  |
| created_at | DATETIME | no | default now() |
| tenant_id | UUID | no | FK tenants.id |
Indexes: ix_witnesses_loan_id, ix_witnesses_tenant_id
