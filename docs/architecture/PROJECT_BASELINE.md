# DAPRO - Project Baseline

> **Update 2026-11-06 (later the same day):** the project was relocated to `C:\Users\user\Projects\DAPRO-platform`
> (the OneDrive copy is a backup only) and the Compose project was renamed from `dapro-ent` to `dapro-platform`
> with services `postgres, redis, backend, celery-worker, celery-beat, frontend`. The tables below record the
> starting state as found and are kept unchanged for traceability. Current setup: `../DOCKER_SETUP.md`.

| Item | Value |
|---|---|
| Baseline date | 2026-11-06 |
| Working directory | `Insp Total Work/DAPRO` (OneDrive) |
| Primary scope source | DAPRO-RD-001 v1.0 (draft for client review, not approved for build commitment) |
| Technical reference | DAPRO-LLD-001 v1.0 (draft) - applied only where it agrees with RD-001 |
| Use-case source | DAPRO-UC-001 v1.0 (Epics, 38 use cases, 8 scenarios) |
| Source copies | `docs/source/` |

## 1. Starting state (inspected before any change)

| Check | Finding |
|---|---|
| Repository contents | The `DAPRO` folder was **empty**. A folder named `DAPRO` (containing the previous `dapro-platform` implementation, 436 source files, no `.git`) had been moved to the Windows Recycle Bin at 00:10 on 2026-11-06. |
| Decision | The product owner chose a **from-scratch rebuild** because the previous UI was not enterprise-grade. The recycled copy was not restored and is not used as a baseline; it remains in the Recycle Bin. |
| Git | No repository existed. A new repository was initialised in `DAPRO/` (no commits made without approval). |
| Active workers | None for DAPRO. Other local Claude sessions were working on unrelated projects (`aiot-rp2`, `cortex`). |
| Running containers | Old stacks `dapro-app`, `dapro-qa`, `dapro-v1` (from the deleted code) are still running and were left untouched. The new stack uses project name `dapro-ent` and the 84xx port range. |
| Existing volumes | Volume `dapro_pgdata` belongs to the old project and is untouched. The new stack uses `dapro-ent_*` volumes. |
| Phase 1 regression | Not applicable: there is no verified prior implementation in this folder to regress against. Regression is defined against the new test suites. |
| Reference images | Five strategy/marketing slides in `images/` (positioning, moat, integration catalogue). Used for visual identity and product principles, not copied. |

## 2. Environment

| Component | Version / port |
|---|---|
| PostgreSQL | 16.4 (container `dapro-ent-db`, host port 55480) |
| Redis | 7.4 (internal) |
| API | Python 3.12, FastAPI, host port 8410 |
| Worker | Celery 5.4 with beat |
| Web | React 18 + Vite build served by nginx, host port 8480 |
| Dev tooling | Node 24 (host), Docker Compose v5 |

## 3. Conflict register (RD-001 vs LLD-001)

RD-001 is the authority for business scope. Conflicting LLD behaviour is **not implemented** until its authority is established.

| ID | LLD-001 content | RD-001 position | Impact | Resolution in this build |
|---|---|---|---|---|
| CF-01 | Product framed as "Default Investigation and Recovery Intelligence Platform: Trace, Verify, Correlate, Investigate, Recover" | Product boundary: monitoring and coordination; not a tracing, recovery or enforcement product (3.2, OX-05, OX-06) | Positioning, UI language | RD wording used everywhere; no recovery or tracing language in UI |
| CF-02 | Discovery gateway calling third-party data providers (KYC, address lookup) with provider_calls, data_points | OX-06 no covert location or social surveillance; OX-09 provider procurement and legal basis must be approved separately; FR-ADR-07 no inferred addresses | Would create an external data-acquisition capability | **Not implemented.** Tables and endpoints omitted. Open decision OD-26 added |
| CF-03 | Correlation engine with link scores and attribute findings | FR-ADR-07, RD 16.1 "never fuzzy auto-link" | Probabilistic identity matching could mis-attribute data | **Not implemented.** Identity linking uses exact bank reference plus exact normalized name and date of birth; ambiguity goes to human reconciliation |
| CF-04 | Case states INVESTIGATING, REVIEW_REQUIRED, FINDINGS_APPROVED tied to discovery | FR-CAS-02 status list | Different state machine | RD-001 FR-CAS-02 statuses implemented |
| CF-05 | Tenant = single organization (tenants.type BANK/COLLEGE) | FR-ORG-01..04 organizations within a sharing relationship | Cross-organization sharing impossible under single-org RLS | Tenant = programme (client deployment); organizations inside; RLS isolates tenants, services enforce organization, branch and assignment scope |
| CF-06 | Usage metering per investigation (billing) | 4.4 commercial model not confirmed (OD-24) | Billing logic without approval | Not implemented |
| CF-07 | RS256 JWT, field-level encryption with blind indexes, S3 storage, monthly audit partitions | Not specified by RD; NFR-SEC-02 requires managed-key encryption at rest | Infrastructure-dependent | Deferred, documented in OPEN_DECISIONS (HS256 secret from environment, volume encryption expected at host, local volume storage) |
| CF-08 | Cursor pagination | Not specified | UI expects page totals | Offset pagination with totals; cursor pagination remains an option |
