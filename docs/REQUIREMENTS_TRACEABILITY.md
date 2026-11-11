# DAPRO - Requirements Traceability

Source of truth: `docs/source/DAPRO_Epics_Use_Cases_Scenarios.xlsx` (10 problems, 10 epics E0-E9, 38 use cases,
8 user scenarios) and `docs/source/DAPRO-RD-001-Requirements-v1.0.docx` (draft for client review). Assessed
2026-11-06 against the code in this repository.

Chain per row: **Epic -> Problem -> Use case -> Scenario -> Frontend route -> API -> Service -> Tables -> Tests**.

## Status legend

| Status | Meaning |
|---|---|
| IMPLEMENTED | Working UI + API + persistence, covered by automated tests listed |
| PARTIAL | Core flow works; a named part is missing or manual (see note) |
| MOCK BOUNDARY | Works end to end against a clearly labelled MOCK provider; live integration needs an open decision |
| PENDING DECISION | Behaviour depends on an open client decision (OD-xx); software uses a labelled DEMO_FIXTURE |
| OUT OF RD SCOPE | Listed in the workbook but marked "Not in RD"; only incidental support exists |

Test references: `B:` = backend pytest (`backend/tests/<file>::<test>`), `U:` = frontend unit (vitest),
`E:` = Playwright browser acceptance (`frontend/e2e/<spec>`).

## Problems -> Epics

| Problem | Severity | Epic(s) | Status |
|---|---|---|---|
| PR-01 Borrower identity is fragmented | 16 | E1 | Addressed |
| PR-02 Repayment status not visible or reliable | 20 | E2 | Addressed (MOCK bank feed, OD-06) |
| PR-03 Repayment trouble detected too late | 25 | E3 | Addressed (rules are DEMO_FIXTURE, OD-15) |
| PR-04 Contact lost after graduation/relocation | 20 | E4, E8 | Addressed |
| PR-05 Post-study status unknown | 12 | E5 | Addressed (update request is human-triggered) |
| PR-06 Guarantor information unreliable | 12 | E6 | Addressed |
| PR-07 Follow-up uncoordinated | 16 | E7 | Addressed |
| PR-08 Borrowers cannot correct data or dispute | 15 | E3, E8 | Addressed |
| PR-09 No portfolio view or audit evidence | 9 | E0, E9 | Addressed (pilot baseline comparison partial) |
| PR-10 Lawful, secure college-bank sharing | 15 | E0 | Addressed (legal basis content is a client decision, OD-25) |

## Use cases

### E0 Platform foundation and trust (PR-10, PR-09)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-01 | Onboard college and bank as separate organisations | US-01 | `/admin/organizations` | `GET/POST/PATCH /admin/organizations`, `/admin/org-units`, `/admin/sharing-agreements` | `admin/orgs.py` | organizations, org_units, sharing_agreements | B: test_admin::test_org_management_permissions, test_foundation::test_rls_isolates_tenants | IMPLEMENTED |
| UC-02 | Users and roles with least privilege | US-01 | `/admin/users`, `/admin/roles`, `/accept-invite` | `/admin/users/*`, `/admin/roles`, `/admin/permissions`, `/admin/sessions` | `admin/users.py`, `core/permissions.py` | users, roles, user_roles, user_sessions | B: test_admin::test_invitation_flow_and_status_lifecycle, ::test_sod_conflict_rejected, ::test_role_must_fit_org_and_scope, test_foundation::test_every_route_declares_permission; E: admin.spec | IMPLEMENTED (MFA enforcement for privileged roles pending OD-20) |
| UC-03 | Record notice and lawful basis | US-01 | Student 360 > Contacts & consent | `GET/POST /students/{id}/consents`, `POST /consents/{id}/withdraw` | `lifecycle/service.py` | consents (notice_version, purpose) | B: test_lifecycle::test_contacts_and_consents, test_comms::test_withdrawn_consent_blocks | IMPLEMENTED (legal wording pending OD-25) |

### E1 Student 360 identity (PR-01)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-04 | Import college student records | US-01 | `/students/import`, `/imports/:id` | `/students/imports`, `/students/imports/{id}/apply`, `/students/imports/template` | `students/imports.py`, worker `dapro.imports.process_student_csv` | import_batches, students | B: test_students::test_csv_import_flow | IMPLEMENTED (CSV only; SIS NOT_CONFIGURED, OD-07) |
| UC-05 | Link student to bank-owned loan | US-01 | `/loans/link` | `POST /loans/link`, `GET /reconciliation`, `POST /reconciliation/{id}/resolve` | `loans/service.py`, `loans/sync.py` | loan_accounts, reconciliation_items | B: test_loans::test_link_happy_path_syncs_bank_data, ::test_ambiguous_link_goes_to_reconciliation_then_confirm, ::test_link_not_found_and_duplicate; E: loans.spec (Journey 3) | IMPLEMENTED (exact match only, never fuzzy) |
| UC-06 | Resolve possible duplicates | US-01 | `/students/duplicates` | `GET /students/duplicates`, `POST /students/duplicates/{id}/resolve` | `students/service.py` | duplicate_candidates, student_field_changes | B: test_students::test_create_duplicate_detection_and_review | IMPLEMENTED |
| UC-07 | View Student 360 | all | `/students/:id` | `GET /students/{id}/profile` | `students/profile.py`, `core/masking.py` | students + related | B: test_students::test_college_profile_hides_bank_amounts, ::test_other_college_gets_404; E: operations.spec (access logged) | IMPLEMENTED |

### E2 Repayment mirror (PR-02)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-08 | Ingest schedules and transactions | US-03 | `/imports`, `/admin/integrations` | `POST /banks/{bank_org_id}/sync`, `GET /imports` | `loans/bank_feed.py`, `loans/sync.py`, worker `dapro.bank.sync_all` | mock_bank_records, repayment_schedules, schedule_instalments, repayment_transactions, loan_snapshots, import_batches | B: test_foundation::test_duplicate_sync_is_idempotent, test_loans::test_sync_endpoint_scoped_to_own_bank | MOCK BOUNDARY (OD-06) |
| UC-09 | View repayment status and DPD | US-04, US-05 | `/loans/:id`, `/repayments` | `GET /loans/{id}`, `/loans/{id}/schedule`, `/loans/{id}/transactions`, `/repayments/overview`, `/repayments/accounts` | `repayments/engine.py` | loan_accounts, schedule_instalments, repayment_transactions | B: test_foundation::test_dpd_classification_rules, test_repayments::test_repayment_overview_and_accounts; E: loans.spec (Journey 4) | IMPLEMENTED (bucket/grace values DEMO_FIXTURE, OD-08) |
| UC-10 | Failed or stale bank sync | US-06 | `/admin/integrations` (simulate failure), freshness badges | `PATCH /admin/integrations/{id}` | `loans/sync.py`, worker `dapro.bank.mark_stale` | integrations, loan_accounts.sync_state | B: test_foundation::test_sync_failure_produces_unknown_not_overdue, test_repayments::test_stale_loans_never_reported_as_paid_or_zero, test_risk::test_stale_data_is_a_data_alert_not_delinquency | IMPLEMENTED |
| UC-11 | Reconcile repayment mismatches | US-05, US-06 | `/reconciliation` | `GET /reconciliation`, `POST /reconciliation/{id}/resolve` | `loans/service.py` | reconciliation_items | B: test_loans::test_ambiguous_link_goes_to_reconciliation_then_confirm; E: loans.spec | IMPLEMENTED |

### E3 Early warning (PR-03, PR-08)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-12 | Raise explainable risk indicator | US-04, US-06 | `/risk`, `/risk/:id` | `GET /risk/indicators`, `GET /risk/indicators/{id}`, `POST /risk/run` | `risk/engine.py`, worker `dapro.risk.nightly` | risk_rules, risk_indicators | B: test_risk::test_indicator_detail_is_explainable, ::test_indicator_wording_is_neutral, ::test_reevaluation_does_not_duplicate | IMPLEMENTED (8 rules are DEMO_FIXTURE, OD-15) |
| UC-13 | Alert before first missed EMI | US-03 | `/risk` (MORATORIUM_ENDING) | as UC-12 | rule `MORATORIUM_ENDING` | risk_indicators | B: test_risk (rule catalogue evaluation) | IMPLEMENTED (window = DEMO_FIXTURE) |
| UC-14 | Review and decide on indicator | US-03, US-04, US-05 | `/risk/:id` | `POST /risk/indicators/{id}/decision`, `/assign` | `risk/service.py` | risk_reviews, cases | B: test_risk::test_decision_requires_rationale_and_creates_case, ::test_field_officer_cannot_decide, test_comms::test_open_amount_dispute_pauses_reminders | IMPLEMENTED |
| UC-15 | Change a risk rule safely | - | `/risk/rules` | `GET /risk/rules`, `POST /risk/rules/{code}/versions`, `POST /risk/rules/{id}/test`, `POST /risk/rules/{id}/approve` | `risk/engine.py::dry_run` | risk_rules | B: test_risk::test_rule_versioning_with_second_approver, ::test_rule_author_cannot_approve_own_version | IMPLEMENTED |

### E4 Contact and address (PR-04)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-16 | Submit address/contact update | US-02 | `/portal/profile`, Student 360 | `POST /portal/address`, `GET/POST /students/{id}/addresses`, `POST /students/{id}/contacts` | `portal/service.py`, `lifecycle/service.py` | student_addresses, student_contacts | B: test_portal::test_address_and_employment_updates_are_borrower_reported, test_lifecycle::test_address_history_preserved_and_audited; E: portal.spec | IMPLEMENTED |
| UC-17 | Verify an address | US-02 | `/verifications` | `POST /addresses/{id}/verification-requests`, `GET /address-verifications`, `POST /address-verifications/{id}/outcome` | `lifecycle/service.py` | student_addresses, address_verifications | B: test_lifecycle::test_verification_workflow | IMPLEMENTED (methods not legally qualified, OD-09) |
| UC-18 | Handle disputed address | - | Student 360, `/grievances` (ADDRESS_DISPUTE) | `POST /addresses/{id}/dispute`, `POST /grievances` | `lifecycle/service.py`, `grievances/service.py` | student_addresses, grievances | B: test_lifecycle::test_dispute_address | IMPLEMENTED |
| UC-19 | Protect historical addresses | - | Student 360 history tab | `GET /students/{id}/addresses` (history is role-gated in the service) | `lifecycle/service.py`, `core/audit.py` | audit_events | B: test_lifecycle::test_address_history_preserved_and_audited | IMPLEMENTED |
| UC-20 | Keep borrowers abroad reachable | US-02 | `/portal/profile` (country), contact preferences | `POST /portal/address`, `PUT /students/{id}/contact-preferences` | `portal/service.py`, `lifecycle/service.py` | student_addresses.country, contact_preferences | B: test_comms::test_sms_opt_out_and_quiet_hours_block | OUT OF RD SCOPE (workbook "Not in RD - gap"); country and time zone are stored, no overseas-specific flow |

### E5 Academic and employment lifecycle (PR-05)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-21 | Record academic status and graduation | US-02 | Student 360 > Academic | `POST /students/{id}/academic` | `lifecycle/service.py` | academic_records | B: test_lifecycle::test_academic_completion_graduates | IMPLEMENTED |
| UC-22 | Post-study update request at graduation | US-02 | `/risk` (EMPLOYMENT_UPDATE_DUE) then `/communications` send | `POST /communications` | rule `EMPLOYMENT_UPDATE_DUE` + `comms/service.py` | risk_indicators, communications | B: test_risk::test_employment_status_alone_never_triggers_financial_indicator, test_comms::test_reminder_queued_then_delivered_by_mock | PARTIAL: the rule raises a review item and staff send the UPDATE_REQUEST template; no fully automatic send (consistent with human-review principle) |
| UC-23 | Report employment status | US-02 | `/portal/profile` | `POST /portal/employment` | `portal/service.py` | employment_records, student_field_changes | B: test_portal::test_address_and_employment_updates_are_borrower_reported, test_lifecycle::test_employment_history_never_creates_risk | IMPLEMENTED |

### E6 Guarantor and co-applicant (PR-06)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-24 | Maintain guarantor records | US-07 | `/loans/:id` > Parties | `GET/POST /loans/{id}/guarantors`, `PATCH /guarantors/{id}`, `GET /guarantor-approvals`, `POST /guarantors/{id}/approve, /reject` | `parties/service.py` | guarantors, loan_parties | B: test_parties::test_guarantor_change_needs_second_user, ::test_guarantor_contacts_masked_and_scoped | IMPLEMENTED |
| UC-25 | Witnesses separate from guarantors | US-07 | `/loans/:id` > Parties | `GET/POST /loans/{id}/witnesses`, `PATCH /witnesses/{id}` | `parties/service.py` | witnesses | B: test_parties::test_witness_is_separate_and_has_no_liability | IMPLEMENTED |
| UC-26 | Contact a guarantor lawfully | US-07 | `/communications` (GUARANTOR_NOTICE) | `POST /communications` | `comms/service.py` | communications | B: test_parties::test_guarantor_communication_requires_basis, test_comms::test_guarantor_requires_lawful_basis | IMPLEMENTED (MOCK delivery, OD-16) |

### E7 Case and field operations (PR-07)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-27 | Create and assign follow-up case | US-03, US-04 | `/cases`, `/cases/new`, `/cases/:id` | `GET/POST /cases`, `GET/PATCH /cases/{id}`, `/assign`, `/follow-ups`, `/evidence` | `cases/service.py`, `cases/machine.py` | cases, case_events, case_follow_ups, evidence | B: test_cases::test_case_lifecycle_guards, ::test_list_has_display_names_and_open_filter; E: operations.spec | IMPLEMENTED |
| UC-28 | Record a field visit | US-04 | `/field`, `/field/visits/:id` (mobile) | `GET /field/my-cases`, `POST /cases/{id}/visits`, `POST /visits/{id}/check-in, /check-out, /submit` | `field/service.py` | field_visits, evidence | B: test_field::test_visit_flow_check_in_submit_idempotent, ::test_cannot_record_visit_on_unassigned_case; E: mobile.spec | IMPLEMENTED (location capture disabled, OD-14; offline drafts not implemented) |
| UC-29 | Record payment commitment | US-04 | `/cases/:id` > Commitments | `POST /cases/{id}/commitments`, `POST /commitments/{id}/confirm` | `cases/service.py` | payment_commitments | B: test_cases::test_case_lifecycle_guards | IMPLEMENTED (shown as borrower-reported, never as payment) |
| UC-30 | Supervise reports and safety incidents | US-04 | `/field/review` | `GET /field/review-queue`, `POST /visits/{id}/review` | `field/service.py` | field_visits | B: test_field::test_safety_incident_goes_to_supervisor_review | IMPLEMENTED |
| UC-31 | Close case on bank confirmation | US-04 | `/cases/:id` transitions | `POST /cases/{id}/transition` | `cases/machine.py` | cases | B: test_cases::test_case_lifecycle_guards | IMPLEMENTED |

### E8 Borrower engagement and grievance (PR-08, PR-04)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-32 | Approved reminder or update request | US-03 | `/communications`, `/templates` | `GET/POST /communications`, `GET/POST /templates`, `POST /templates/{id}/approve` | `comms/service.py`, worker `dapro.comms.dispatch` | communications, notification_templates, contact_preferences | B: test_comms (all 7 tests) | MOCK BOUNDARY (OD-16); quiet hours/caps are DEMO_FIXTURE |
| UC-33 | Raise and track grievance or correction | US-05 | `/grievances`, `/grievances/:id`, `/portal/grievances` | `/grievances/*`, `/portal/grievances` | `grievances/service.py` | grievances, grievance_events, student_field_changes | B: test_grievances (4 tests); U: PortalGrievancesPage.test; E: grievances.spec (portal -> staff -> portal) | IMPLEMENTED (SLA = DEMO_FIXTURE, OD-18) |
| UC-34 | Borrower self-service portal | - | `/portal`, `/portal/profile`, `/portal/grievances`, `/portal/messages` | `/portal/*` | `portal/service.py` | (reads/writes own records only) | B: test_portal (3 tests); E: portal.spec, mobile.spec | IMPLEMENTED (release decision pending, OD-17) |

### E9 Reporting and audit (PR-09)

| UC | Use case | Scenario | Frontend | API | Service | Tables | Tests | Status |
|---|---|---|---|---|---|---|---|---|
| UC-35 | Portfolio dashboard | US-08 | `/` (Enterprise Cockpit) | `GET /dashboard/summary` | `dashboard/*` | (aggregates over loans, cases, risk, grievances) | B: test_dashboard::test_dashboard_kpis_match_database_for_bank_user, ::test_dashboard_college_and_platform_have_no_financial_amounts | IMPLEMENTED (backend-derived KPIs only) |
| UC-36 | Export data under control | US-08 | `/reports/:code` export panel | `POST /exports`, `GET /exports/{id}/download` | `reports/service.py`, worker `dapro.reports.export` | export_jobs, audit_events | B: test_reports::test_export_requires_purpose_and_is_audited, ::test_field_officer_cannot_export; E: reports-audit.spec | IMPLEMENTED |
| UC-37 | Reconstruct a case for audit | US-08 | `/audit`, `/audit/cases/:id` | `GET /audit/events`, `GET /audit/verify`, `GET /audit/cases/{id}/reconstruction` | `audit/reconstruct.py` | audit_events, audit_checkpoints | B: test_audit::test_case_reconstruction_has_completeness, test_foundation::test_audit_chain_verifies, ::test_audit_trigger_blocks_even_owner | IMPLEMENTED |
| UC-38 | Measure pilot success against baseline | US-08 | `/reports` (14 reports) | `GET /reports/catalog`, `POST /reports/{code}/run` | `reports/runners.py` | - | B: test_reports::test_every_report_runs_with_meta | PARTIAL: operational metrics exist; no baseline import/comparison because the client has not supplied baseline data (RD 3.3) |

## Scenario coverage

| Scenario | Use cases | Automated end-to-end evidence | Status |
|---|---|---|---|
| US-01 New student cohort | UC-01..07 | B: test_students::test_csv_import_flow, test_loans link tests; E: loans.spec | Covered (API + partial browser) |
| US-02 Graduate moves abroad | UC-20..23, 16, 17 | B: test_lifecycle, test_portal; E: portal.spec (address + persistence) | Covered except UC-20 overseas flow (out of RD scope) and automatic UC-22 send |
| US-03 Engage before first missed EMI | UC-08, 13, 14, 27, 32 | B: test_risk, test_comms | Covered at API level |
| US-04 Missed EMI leads to field visit | UC-09, 12, 14, 27, 28, 29, 31 | B: test_risk, test_cases, test_field; E: operations.spec, mobile.spec | Covered |
| US-05 Student disputes amount | UC-33, 14, 11, 09 | B: test_grievances::test_dispute_pauses_case_and_resolution_restores_it, test_comms::test_open_amount_dispute_pauses_reminders; E: grievances.spec | Covered end to end in the browser |
| US-06 Bank data goes stale | UC-10, 12, 11 | B: test_foundation::test_sync_failure_produces_unknown_not_overdue, test_risk::test_stale_data_is_a_data_alert_not_delinquency | Covered at API level |
| US-07 Contact guarantor lawfully | UC-24..26 | B: test_parties, test_comms::test_guarantor_requires_lawful_basis | Covered at API level |
| US-08 Auditor reconstructs a case | UC-37, 36, 35, 38 | B: test_audit, test_reports; E: reports-audit.spec | Covered (UC-38 partial) |

Browser e2e results for the run on 2026-11-06 are recorded in `TESTING_AND_VALIDATION.md`.
