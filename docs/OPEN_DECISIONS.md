# DAPRO - Open Decisions

RD-001 section 17 decisions remain **open**. Nothing below has been silently converted into an approved rule.
Where the software needs a value to run, it uses a versioned policy record labelled `DEMO_FIXTURE` (visible in the UI)
or shows `NOT_CONFIGURED`.

| ID | Decision (RD-001) | How the build behaves until decided |
|---|---|---|
| OD-01 | Legal meaning of "loan provider: college" | Colleges and banks are separate organizations; banks own loan accounts |
| OD-02 | Bank ownership model | Bank is source of truth for all loan financials (BR-01) |
| OD-03 | Borrower definition | Applicant + optional co-applicant parties; no liability inferred |
| OD-04 | Target institutions | Multi-college, multi-bank supported; demo uses 2 + 2 |
| OD-05 | Pilot volumes | Demo: 172 students, ~170 loans; no performance targets claimed |
| OD-06 | Bank integration method | **Only a MOCK bank feed exists**, labelled MOCK everywhere. No live API |
| OD-07 | College integration | CSV import (DAPRO CSV v1) for students; RCE SIS shows NOT_CONFIGURED |
| OD-08 | Repayment semantics | DPD uses bank-supplied allocation; grace days and buckets are DEMO_FIXTURE policy |
| OD-09 | Address verification methods | Methods recorded (document, postal, field visit, phone, self-declaration); none treated as legally sufficient |
| OD-10 | Employment data | Voluntary; no income field collected |
| OD-11 | Guarantor scope | Agreement reference required; communication only when explicitly permitted |
| OD-12 | Witness records | Implemented separately from guarantors (can be switched off if not needed) |
| OD-13 | Field authority | Field officers belong to the bank organization in the demo |
| OD-14 | Location capture | **Disabled.** Check-in/out records time only; no coordinates stored |
| OD-15 | Risk policy | 8 explainable rules as DEMO_FIXTURE; severity labels pending approval |
| OD-16 | Communication channels | Email and SMS are MOCK providers; nothing is delivered to real recipients |
| OD-17 | Borrower portal | Implemented for demonstration; release decision pending |
| OD-18 | Grievance ownership and SLA | 15-day SLA as DEMO_FIXTURE |
| OD-19 | Hosting and data residency | Docker Compose reference deployment only |
| OD-20 | Identity provider | DAPRO-managed identities with optional TOTP MFA; MFA enforcement for privileged roles pending |
| OD-21 | Retention and deletion | No purge job enabled; audit retained indefinitely |
| OD-22 | Availability and support | Not defined; health and metrics endpoints provided |
| OD-23 | Reporting | 14 proposed reports; client must confirm |
| OD-24 | Commercial model | No metering implemented |
| OD-25 | Regulatory responsibility | Not decided; no legal notices or recovery actions exist in the product |
| OD-26 (new) | Third-party data providers proposed in LLD-001 (discovery gateway) | Not implemented; requires legal basis, procurement and RD change request (conflict CF-02) |
| OD-27 (new) | Field-level encryption, key management, object storage | Deferred to hosting decision (CF-07) |
| OD-28 (new, 2026-11-06) | May the maker withdraw or reject their own draft policy / rule / template version? | Strict reading of BR-12 applied: the maker can neither approve nor reject their own draft; a second authorised user decides. The UI explains this. |
| OD-29 (new, 2026-11-06) | Who may approve programme-wide policies (`policy_configs` are tenant-wide)? | Any user holding `policy:manage` in the tenant, other than the maker, may approve. In the demo this includes a bank administrator of a different bank. Client to confirm governance (e.g. platform or programme owner only). |
| OD-30 (new, 2026-11-06) | Production identity of field officers and agencies (AGENCY organization type exists) | Demo field officers belong to the bank (see OD-13); agency onboarding needs a contractual and data-sharing basis. |

## Review status

Decisions OD-01 to OD-25 come from RD-001 section 17 and remain **open** pending client review. OD-26 to OD-30
were raised during the build. None has been converted into an approved business rule; values the software
needs are `DEMO_FIXTURE` policy versions visible under Administration > Policy configuration.
