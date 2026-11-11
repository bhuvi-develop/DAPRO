# DAPRO - API Inventory

Generated from the FastAPI application (`backend/scripts/gen_docs.py`). Base path `/api/v1`. Interactive OpenAPI: `/api/v1/docs`, schema: `/api/v1/openapi.json`.

Conventions: Bearer access token; X-Correlation-ID echoed; error envelope `{error:{code,message,next_step,correlation_id,details}}`; list endpoints return `{items,total,page,size}`; money as decimal strings; financial blocks carry `freshness`.

Total operations: 160

| Module | Method | Path | Permission | Operation |
|---|---|---|---|---|
|  | GET | `/metrics` | - | metrics |
| admin | POST | `/api/v1/admin/demo/reset` | demo:reset | demo reset |
| admin | GET | `/api/v1/admin/integrations` | integration:read | list integrations |
| admin | PATCH | `/api/v1/admin/integrations/{integration_id}` | integration:manage | update integration |
| admin | GET | `/api/v1/admin/org-units` | org:read | list units |
| admin | POST | `/api/v1/admin/org-units` | org:manage, user:manage | create unit |
| admin | GET | `/api/v1/admin/organizations` | org:read | list orgs |
| admin | POST | `/api/v1/admin/organizations` | org:manage | create org |
| admin | PATCH | `/api/v1/admin/organizations/{org_id}` | org:manage | update org |
| admin | GET | `/api/v1/admin/permissions` | role:read | permissions |
| admin | GET | `/api/v1/admin/policies` | policy:read | list policies |
| admin | POST | `/api/v1/admin/policies` | policy:manage | propose policy |
| admin | POST | `/api/v1/admin/policies/{policy_id}/approve` | policy:manage | approve policy |
| admin | POST | `/api/v1/admin/policies/{policy_id}/reject` | policy:manage | reject policy |
| admin | GET | `/api/v1/admin/roles` | role:read | list roles |
| admin | GET | `/api/v1/admin/sessions` | session:manage | list sessions |
| admin | DELETE | `/api/v1/admin/sessions/{session_id}` | session:manage | revoke session |
| admin | GET | `/api/v1/admin/sharing-agreements` | org:read | list agreements |
| admin | POST | `/api/v1/admin/sharing-agreements` | org:manage | create agreement |
| admin | GET | `/api/v1/admin/users` | user:read | list users |
| admin | POST | `/api/v1/admin/users/invite` | user:manage | invite |
| admin | GET | `/api/v1/admin/users/{user_id}` | user:read | get user |
| admin | POST | `/api/v1/admin/users/{user_id}/activate` | user:manage | activate |
| admin | POST | `/api/v1/admin/users/{user_id}/resend-invitation` | user:manage | resend |
| admin | POST | `/api/v1/admin/users/{user_id}/revoke` | user:manage | revoke |
| admin | PUT | `/api/v1/admin/users/{user_id}/roles` | user:manage | set roles |
| admin | POST | `/api/v1/admin/users/{user_id}/suspend` | user:manage | suspend |
| admin | POST | `/api/v1/admin/users/{user_id}/unlock` | user:manage | unlock |
| audit | GET | `/api/v1/audit/cases/{case_id}/reconstruction` | audit:read | case reconstruction |
| audit | GET | `/api/v1/audit/checkpoints` | audit:verify | checkpoints |
| audit | GET | `/api/v1/audit/events` | audit:read | events |
| audit | GET | `/api/v1/audit/verify` | audit:verify | verify |
| auth | POST | `/api/v1/auth/invitations/accept` | public | accept invitation |
| auth | POST | `/api/v1/auth/login` | public | login |
| auth | POST | `/api/v1/auth/logout` | authenticated | logout |
| auth | POST | `/api/v1/auth/logout-cookie` | public | logout cookie |
| auth | GET | `/api/v1/auth/me` | authenticated | me |
| auth | POST | `/api/v1/auth/mfa/enable` | authenticated | mfa enable |
| auth | POST | `/api/v1/auth/mfa/setup` | authenticated | mfa setup |
| auth | POST | `/api/v1/auth/mfa/verify` | public | mfa verify |
| auth | POST | `/api/v1/auth/password` | authenticated | change password |
| auth | POST | `/api/v1/auth/refresh` | public | refresh |
| auth | GET | `/api/v1/auth/sessions` | authenticated | my sessions |
| auth | DELETE | `/api/v1/auth/sessions/{session_id}` | authenticated | revoke my session |
| borrower-portal | POST | `/api/v1/portal/address` | portal:self | address |
| borrower-portal | GET | `/api/v1/portal/communications` | portal:self | my comms |
| borrower-portal | POST | `/api/v1/portal/employment` | portal:self | employment |
| borrower-portal | GET | `/api/v1/portal/grievances` | portal:self | my grievances |
| borrower-portal | POST | `/api/v1/portal/grievances` | portal:self | raise grievance |
| borrower-portal | GET | `/api/v1/portal/grievances/{gid}` | portal:self | my grievance |
| borrower-portal | GET | `/api/v1/portal/overview` | portal:self | overview |
| borrower-portal | GET | `/api/v1/portal/profile` | portal:self | profile |
| cases | GET | `/api/v1/cases` | case:read | list cases |
| cases | POST | `/api/v1/cases` | case:create | create |
| cases | GET | `/api/v1/cases/meta` | case:read | meta |
| cases | GET | `/api/v1/cases/{case_id}` | case:read | get |
| cases | PATCH | `/api/v1/cases/{case_id}` | case:update, case:assign | patch |
| cases | POST | `/api/v1/cases/{case_id}/assign` | case:assign | assign |
| cases | POST | `/api/v1/cases/{case_id}/commitments` | case:update | commitment |
| cases | POST | `/api/v1/cases/{case_id}/evidence` | case:update | evidence |
| cases | POST | `/api/v1/cases/{case_id}/follow-ups` | case:update | follow up |
| cases | POST | `/api/v1/cases/{case_id}/transition` | case:read | transition |
| cases | POST | `/api/v1/commitments/{commitment_id}/confirm` | case:update, case:close | confirm |
| cases | GET | `/api/v1/evidence/{evidence_id}/download` | case:read | download |
| communications | GET | `/api/v1/communications` | comm:read | list comms |
| communications | POST | `/api/v1/communications` | comm:send | send |
| communications | GET | `/api/v1/students/{student_id}/communications` | comm:read | student comms |
| communications | GET | `/api/v1/templates` | comm:read, template:manage, comm:send | templates |
| communications | POST | `/api/v1/templates` | template:manage | create template |
| communications | POST | `/api/v1/templates/{template_id}/approve` | template:manage | approve |
| dashboard | GET | `/api/v1/dashboard/summary` | dashboard:read | summary |
| field | POST | `/api/v1/cases/{case_id}/visits` | visit:record | create |
| field | GET | `/api/v1/field/meta` | visit:record, visit:review | meta |
| field | GET | `/api/v1/field/my-cases` | visit:record | my cases |
| field | GET | `/api/v1/field/review-queue` | visit:review | queue |
| field | GET | `/api/v1/visits/{visit_id}` | visit:record, visit:review | get |
| field | PATCH | `/api/v1/visits/{visit_id}` | visit:record | save |
| field | POST | `/api/v1/visits/{visit_id}/check-in` | visit:record | check in |
| field | POST | `/api/v1/visits/{visit_id}/check-out` | visit:record | check out |
| field | POST | `/api/v1/visits/{visit_id}/review` | visit:review | review |
| field | POST | `/api/v1/visits/{visit_id}/submit` | visit:record | submit |
| grievances | GET | `/api/v1/grievances` | grievance:read | list grievances |
| grievances | POST | `/api/v1/grievances` | grievance:create | create |
| grievances | GET | `/api/v1/grievances/meta` | grievance:read | meta |
| grievances | GET | `/api/v1/grievances/{gid}` | grievance:read | get |
| grievances | POST | `/api/v1/grievances/{gid}/assign` | grievance:manage | assign |
| grievances | POST | `/api/v1/grievances/{gid}/respond` | grievance:manage | respond |
| grievances | POST | `/api/v1/grievances/{gid}/transition` | grievance:manage | transition |
| guarantors-witnesses | GET | `/api/v1/guarantor-approvals` | guarantor:approve | pending |
| guarantors-witnesses | PATCH | `/api/v1/guarantors/{guarantor_id}` | guarantor:write | update guarantor |
| guarantors-witnesses | POST | `/api/v1/guarantors/{guarantor_id}/approve` | guarantor:approve | approve |
| guarantors-witnesses | POST | `/api/v1/guarantors/{guarantor_id}/reject` | guarantor:approve | reject |
| guarantors-witnesses | GET | `/api/v1/loans/{loan_id}/guarantors` | guarantor:read | list guarantors |
| guarantors-witnesses | POST | `/api/v1/loans/{loan_id}/guarantors` | guarantor:write | create guarantor |
| guarantors-witnesses | GET | `/api/v1/loans/{loan_id}/witnesses` | witness:read | list witnesses |
| guarantors-witnesses | POST | `/api/v1/loans/{loan_id}/witnesses` | witness:write | create witness |
| guarantors-witnesses | PATCH | `/api/v1/witnesses/{witness_id}` | witness:write | update witness |
| lifecycle | GET | `/api/v1/address-verifications` | address:verify | verification queue |
| lifecycle | POST | `/api/v1/address-verifications/{verification_id}/outcome` | address:verify | record outcome |
| lifecycle | POST | `/api/v1/addresses/{address_id}/dispute` | address:write | dispute |
| lifecycle | POST | `/api/v1/addresses/{address_id}/verification-requests` | address:write, address:verify | request verification |
| lifecycle | POST | `/api/v1/consents/{consent_id}/withdraw` | student:write | withdraw consent |
| lifecycle | POST | `/api/v1/employment/{record_id}/verify` | employment:write | verify employment |
| lifecycle | POST | `/api/v1/students/{student_id}/academic` | academic:write | add academic |
| lifecycle | GET | `/api/v1/students/{student_id}/addresses` | address:read | list addresses |
| lifecycle | POST | `/api/v1/students/{student_id}/addresses` | address:write | add address |
| lifecycle | GET | `/api/v1/students/{student_id}/consents` | student:read | list consents |
| lifecycle | POST | `/api/v1/students/{student_id}/consents` | student:write | add consent |
| lifecycle | GET | `/api/v1/students/{student_id}/contact-preferences` | student:read | get preferences |
| lifecycle | PUT | `/api/v1/students/{student_id}/contact-preferences` | student:write | set preference |
| lifecycle | POST | `/api/v1/students/{student_id}/contacts` | address:write | add contact |
| lifecycle | GET | `/api/v1/students/{student_id}/employment` | student:read | list employment |
| lifecycle | POST | `/api/v1/students/{student_id}/employment` | employment:write | add employment |
| loans | POST | `/api/v1/banks/{bank_org_id}/sync` | bank:sync | sync bank |
| loans | GET | `/api/v1/imports` | bank:sync, student:import, integration:read | list imports |
| loans | GET | `/api/v1/imports/{batch_id}` | bank:sync, student:import, integration:read | get import |
| loans | GET | `/api/v1/loans` | loan:read | list loans |
| loans | POST | `/api/v1/loans/link` | loan:link | link loan |
| loans | GET | `/api/v1/loans/{loan_id}` | loan:read | get loan |
| loans | GET | `/api/v1/loans/{loan_id}/schedule` | loan:read, repayment:read | get schedule |
| loans | GET | `/api/v1/loans/{loan_id}/snapshots` | loan:read, loan:financial | get snapshots |
| loans | GET | `/api/v1/loans/{loan_id}/transactions` | loan:read, repayment:read | get transactions |
| loans | GET | `/api/v1/reconciliation` | loan:reconcile | list reconciliation |
| loans | POST | `/api/v1/reconciliation/{item_id}/resolve` | loan:reconcile | resolve item |
| notifications | GET | `/api/v1/notifications` | authenticated | list notifications |
| notifications | POST | `/api/v1/notifications/read-all` | authenticated | read all |
| notifications | GET | `/api/v1/notifications/unread-count` | authenticated | unread count |
| notifications | POST | `/api/v1/notifications/{notification_id}/read` | authenticated | mark read |
| platform | GET | `/api/v1/health` | public | health |
| repayments | GET | `/api/v1/repayments/accounts` | repayment:read | accounts |
| repayments | GET | `/api/v1/repayments/overview` | repayment:read | overview |
| reports | GET | `/api/v1/exports` | export:create, audit:read | list exports |
| reports | POST | `/api/v1/exports` | export:create | create export |
| reports | GET | `/api/v1/exports/{job_id}/download` | export:create, audit:read | download |
| reports | GET | `/api/v1/reports/catalog` | report:read | report catalog |
| reports | POST | `/api/v1/reports/{code}/run` | report:read | run report |
| risk | GET | `/api/v1/risk/indicators` | risk:read | indicators |
| risk | GET | `/api/v1/risk/indicators/{ind_id}` | risk:read | indicator |
| risk | POST | `/api/v1/risk/indicators/{ind_id}/assign` | risk:decide | assign |
| risk | POST | `/api/v1/risk/indicators/{ind_id}/decision` | risk:decide | decision |
| risk | GET | `/api/v1/risk/meta` | risk:read, policy:read | meta |
| risk | GET | `/api/v1/risk/rules` | risk:read, policy:read | rules |
| risk | POST | `/api/v1/risk/rules/{code}/versions` | risk:rules | propose |
| risk | POST | `/api/v1/risk/rules/{rule_id}/approve` | risk:approve_rules | approve |
| risk | POST | `/api/v1/risk/rules/{rule_id}/test` | risk:rules, risk:approve_rules | test rule |
| risk | POST | `/api/v1/risk/run` | risk:decide | run |
| search | GET | `/api/v1/search` | dashboard:read | search |
| students | GET | `/api/v1/students` | student:read | list students |
| students | POST | `/api/v1/students` | student:write | create student |
| students | GET | `/api/v1/students/duplicates` | student:merge | duplicates |
| students | POST | `/api/v1/students/duplicates/{dup_id}/resolve` | student:merge | resolve duplicate |
| students | GET | `/api/v1/students/imports` | student:import | list imports |
| students | POST | `/api/v1/students/imports` | student:import | upload import |
| students | GET | `/api/v1/students/imports/template` | student:import | import template |
| students | GET | `/api/v1/students/imports/{batch_id}` | student:import | get import |
| students | POST | `/api/v1/students/imports/{batch_id}/apply` | student:import | apply import |
| students | GET | `/api/v1/students/{student_id}` | student:read | get student |
| students | PATCH | `/api/v1/students/{student_id}` | student:write | update student |
| students | GET | `/api/v1/students/{student_id}/history` | student:read | field history |
| students | GET | `/api/v1/students/{student_id}/profile` | student:read | student profile |