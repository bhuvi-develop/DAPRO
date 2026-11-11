"""Permission catalogue and default role matrix (RD section 6, LLD section 4).

The matrix is a PROPOSED default (RD section 6: the client must approve the final matrix).
Scope is evaluated separately from permission: organization, branch and case assignment.
"""

PERMISSIONS: dict[str, str] = {
    "dashboard:read": "View role-scoped dashboard",
    "org:read": "View organizations and units",
    "org:manage": "Create and change organizations, units and sharing agreements",
    "user:read": "View users",
    "user:manage": "Invite, activate, suspend and revoke users; change roles",
    "role:read": "View roles and permission matrix",
    "session:manage": "View and revoke sessions of other users",
    "integration:read": "View integration status",
    "integration:manage": "Configure integrations",
    "policy:read": "View policy configuration",
    "policy:manage": "Propose and approve policy configuration",
    "student:read": "View student profiles (role-masked)",
    "student:write": "Register and update student records",
    "student:import": "Import student records",
    "student:merge": "Resolve duplicate candidates",
    "student:pii_full": "View unmasked contact details",
    "loan:read": "View linked loan accounts (non-financial fields)",
    "loan:financial": "View bank-sourced financial amounts",
    "loan:link": "Link students to bank loan references",
    "loan:reconcile": "Work the reconciliation queue",
    "bank:sync": "Trigger bank data synchronization and imports",
    "repayment:read": "View repayment schedules, transactions and DPD",
    "address:read": "View current addresses",
    "address:history": "View historical addresses (audited)",
    "address:write": "Submit address and contact updates",
    "address:verify": "Record address verification outcomes",
    "academic:write": "Record academic status",
    "employment:write": "Record employment status",
    "guarantor:read": "View guarantor records",
    "guarantor:write": "Maintain guarantor records",
    "guarantor:approve": "Approve guarantor changes (second user)",
    "witness:read": "View witness records",
    "witness:write": "Maintain witness records",
    "risk:read": "View risk indicators",
    "risk:decide": "Record risk review decisions",
    "risk:rules": "Propose risk rule versions",
    "risk:approve_rules": "Approve risk rule versions",
    "case:read": "View cases in scope",
    "case:create": "Open follow-up cases",
    "case:assign": "Assign and reassign cases",
    "case:update": "Update case details, follow-ups and evidence",
    "case:escalate": "Escalate cases",
    "case:close": "Resolve and close cases",
    "visit:record": "Record field visits (assigned cases only)",
    "visit:review": "Supervise field visit reports",
    "comm:read": "View communication history",
    "comm:send": "Send approved communications",
    "comm:guarantor": "Send guarantor communications (lawful basis required)",
    "template:manage": "Create and approve notification templates",
    "grievance:read": "View grievances",
    "grievance:create": "Log grievances on behalf of borrowers",
    "grievance:manage": "Own, respond to and resolve grievances",
    "report:read": "Run reports",
    "export:create": "Export report data (purpose-logged)",
    "audit:read": "Search audit events and reconstruct cases",
    "audit:verify": "Run audit chain verification",
    "demo:reset": "Reset the DEMO dataset",
    "portal:self": "Borrower self-service (own records only)",
}

_STAFF_BASE = ["dashboard:read", "org:read"]

ROLE_MATRIX: dict[str, dict] = {
    "PLATFORM_ADMIN": {
        "name": "Platform Administrator", "org_types": ["PLATFORM"],
        "description": "Tenant setup and technical configuration. No default access to borrower financial content.",
        "permissions": _STAFF_BASE + ["org:manage", "user:read", "user:manage", "role:read", "session:manage",
                                      "integration:read", "integration:manage", "policy:read", "audit:verify",
                                      "demo:reset"],
    },
    "COLLEGE_ADMIN": {
        "name": "College Administrator", "org_types": ["COLLEGE"],
        "description": "Manages college users, academic master data and student records. No bank ledger access.",
        "permissions": _STAFF_BASE + ["user:read", "user:manage", "role:read", "student:read", "student:write",
                                      "student:import", "student:merge", "student:pii_full", "loan:read",
                                      "address:read", "address:write", "academic:write", "employment:write",
                                      "grievance:read", "grievance:create", "grievance:manage", "comm:read",
                                      "report:read", "export:create", "integration:read", "policy:read"],
    },
    "COLLEGE_OFFICER": {
        "name": "College Student-Services Officer", "org_types": ["COLLEGE"],
        "description": "Views permitted student profiles and submits academic and contact updates.",
        "permissions": _STAFF_BASE + ["student:read", "student:write", "loan:read", "address:read",
                                      "address:write", "academic:write", "employment:write", "grievance:read",
                                      "grievance:create", "comm:read"],
    },
    "BANK_ADMIN": {
        "name": "Bank Administrator", "org_types": ["BANK", "NBFC"],
        "description": "Manages bank users, branches, permissions and integration configuration.",
        "permissions": _STAFF_BASE + ["user:read", "user:manage", "role:read", "session:manage",
                                      "integration:read", "integration:manage", "policy:read", "policy:manage",
                                      "template:manage", "student:read", "loan:read", "report:read"],
    },
    "BANK_LOAN_OPS": {
        "name": "Bank Loan Operations", "org_types": ["BANK", "NBFC"],
        "description": "Views bank loan and repayment data, links loans, reconciles and approves case outcomes.",
        "permissions": _STAFF_BASE + ["student:read", "loan:read", "loan:financial", "loan:link", "loan:reconcile",
                                      "bank:sync", "repayment:read", "address:read", "address:history",
                                      "address:verify", "guarantor:read", "guarantor:write", "guarantor:approve",
                                      "witness:read", "witness:write", "risk:read", "case:read", "case:create",
                                      "case:close", "comm:read", "comm:send", "comm:guarantor", "grievance:read",
                                      "grievance:create", "grievance:manage", "report:read", "export:create",
                                      "integration:read", "policy:read", "risk:approve_rules"],
    },
    "INVESTIGATION_OFFICER": {
        "name": "Investigation Officer", "org_types": ["BANK", "NBFC", "AGENCY"],
        "description": "Works follow-up cases in scope: records contact attempts, evidence and borrower updates.",
        "permissions": _STAFF_BASE + ["student:read", "loan:read", "loan:financial", "repayment:read",
                                      "address:read", "address:write", "employment:write", "guarantor:read",
                                      "witness:read", "risk:read", "case:read", "case:create", "case:update",
                                      "comm:read", "comm:send", "grievance:read", "grievance:create"],
    },
    "COLLECTIONS_MANAGER": {
        "name": "Collections / Follow-up Manager", "org_types": ["BANK", "NBFC", "AGENCY"],
        "description": "Reviews portfolio, allocates cases, approves escalations, supervises field conduct.",
        "permissions": _STAFF_BASE + ["student:read", "loan:read", "loan:financial", "repayment:read",
                                      "address:read", "address:history", "guarantor:read", "witness:read",
                                      "risk:read", "risk:decide", "risk:rules", "case:read", "case:create",
                                      "case:assign", "case:update", "case:escalate", "case:close",
                                      "visit:review", "comm:read", "comm:send", "grievance:read",
                                      "grievance:create", "grievance:manage", "report:read", "export:create",
                                      "user:read", "policy:read"],
    },
    "FIELD_OFFICER": {
        "name": "Field Officer", "org_types": ["BANK", "NBFC", "AGENCY"],
        "description": "Assigned cases only. Records approved contact attempts and visits. No export or loan changes.",
        "permissions": ["dashboard:read", "student:read", "loan:read", "address:read", "case:read",
                        "case:update", "visit:record"],
    },
    "AUDITOR": {
        "name": "Auditor / Compliance Reviewer", "org_types": ["BANK", "NBFC", "COLLEGE"],
        "description": "Read-only access to scoped audit evidence and reports.",
        "permissions": _STAFF_BASE + ["student:read", "loan:read", "loan:financial", "repayment:read",
                                      "risk:read", "case:read", "grievance:read", "comm:read", "report:read",
                                      "export:create", "audit:read", "audit:verify", "policy:read",
                                      "integration:read", "user:read", "role:read"],
    },
    "BORROWER": {
        "name": "Borrower / Student", "org_types": ["COLLEGE"],
        "description": "Views own permitted information, submits updates and raises grievances.",
        "permissions": ["portal:self"],
    },
}

# Segregation of duties (RD 6.1, LLD 4): these pairs may not be held by one user.
SOD_CONFLICTS: list[tuple[str, str]] = [
    ("user:manage", "risk:decide"),
    ("user:manage", "case:close"),
    ("user:manage", "loan:financial"),
]

# Roles whose holders must enrol MFA before production use (NFR-SEC-04). Enforcement mode is OD-20.
PRIVILEGED_ROLES = {"PLATFORM_ADMIN", "COLLEGE_ADMIN", "BANK_ADMIN"}


def sod_violations(perms: set[str]) -> list[str]:
    return [f"{a} + {b}" for a, b in SOD_CONFLICTS if a in perms and b in perms]
