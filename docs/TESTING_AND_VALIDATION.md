# DAPRO - Testing and Validation

A page loading is not evidence that a module works, and an HTTP 200 is not evidence that a workflow works. Every
claim below names the layer that proves it and was produced by an actual run on 2026-11-06.

## Layers

| Layer | Tooling | What it proves | Location |
|---|---|---|---|
| Unit | pytest | DPD classification, bucket mapping, state machines, rule logic, configuration guard | `backend/tests` |
| Service + API | pytest + FastAPI TestClient | Validation, permission and scope on real HTTP calls | `backend/tests/test_*.py` |
| Database integration | pytest against PostgreSQL 16 as `dapro_app` | RLS tenant isolation, append-only grants, audit trigger, idempotent sync | `test_foundation.py` |
| Authorization | pytest | Every route declares a permission; negative tests per role | all module tests |
| Migration | Alembic upgrade -> downgrade base -> upgrade | Reversibility of 0001 and 0002 | `scripts/test-migrations.sh` |
| Frontend static | `tsc -b`, ESLint (zero warnings), Vite build | Type safety, hook rules, bundle builds | `frontend/` |
| Frontend unit / component | Vitest + Testing Library | API client contract, form validation, permission-aware UI, formatting | `frontend/src/**/*.test.ts(x)` |
| Browser acceptance | Playwright (Chromium) | Real login, UI workflows across roles, reload persistence, **direct PostgreSQL verification** of rows and audit events, role denial; desktop 1440 px and mobile 360 px | `frontend/e2e/` |

## Results (2026-11-06)

| Gate | Command | Result |
|---|---|---|
| Backend lint | `ruff check app tests` | Pass (0 findings) |
| Backend tests | `pytest -q -p no:warnings` (disposable `dapro_test` DB, current source) | **103 passed**, 0 failed |
| Migrations | `scripts/test-migrations.sh` | Pass: 0001 -> 0002 -> base -> 0002 (head) on scratch DB `dapro_migcheck`, dropped afterwards |
| Frontend typecheck | `npm run typecheck` | Pass |
| Frontend lint | `npm run lint` | Pass (0 errors, 0 warnings) |
| Frontend unit | `npm test` | **15 passed** (4 files) |
| Frontend build | `npx vite build` | Pass |
| Browser acceptance | `npx playwright test` | **24 passed**, 0 failed, 0 skipped (22 desktop + 2 mobile, 7.9 min) |
| Background jobs | worker + beat logs | Worker ready; `dapro.comms.dispatch` executed by beat and succeeded; export job processed (Journey 11) |
| Secret scan | real `.env` values and key patterns over all 327 files to be committed | 0 findings; no `.env`, `node_modules`, build output, caches or logs staged |

### Browser acceptance specs

| Spec | Journeys |
|---|---|
| `admin.spec.ts` | Policy proposal (JSON validation) -> maker cannot decide -> second admin rejects; DB status and audit verified; users/integrations pages; field officer denied |
| `grievances.spec.ts` | Borrower raises an amount dispute in the portal -> manager reviews, responds and resolves -> borrower sees outcome; DB status and two audited transitions; queue filters; borrower cannot open another borrower's grievance |
| `portal.spec.ts` | Own loan with MOCK source and freshness; address update validation, persistence (BORROWER_REPORTED, UNVERIFIED, history kept); messages labelled as not delivered; borrower kept out of staff UI and staff API |
| `loans.spec.ts` | Link an unmatched bank loan with persistence and audit; schedule and transactions with freshness; dashboard deep link; college sees "Restricted" amounts (AC-02); ambiguous link reconciliation |
| `operations.spec.ts` | Student search -> Student 360 with access audit; register form validation; risk queue and case detail; field officer scope |
| `reports-audit.spec.ts` | Run a report, export with a purpose, download, audit record; field officer cannot export; auditor verifies the hash chain |
| `mobile.spec.ts` | Field visit list and all portal pages at 360 px with no horizontal scrolling |

### Environment note for this run

The Docker Desktop VM on the build machine could not reach PyPI, npm or Docker Hub (BLOCKER_REGISTER EXT-01), so
images could not be rebuilt. The browser suite therefore ran against the Vite dev server (`DAPRO_WEB_URL=
http://localhost:5180`) proxying to the real backend container, PostgreSQL and Celery services; the backend image
was the previously built one with the pinned `kombu 5.4.2` installed locally. Re-run the suite against the nginx
container (`http://localhost:8480`, the default) after a networked `docker compose build`.

## Test data and isolation

- Backend tests create a fresh database per run (`DAPRO_TEST_DB`, default `dapro_test`), migrate it as the owner,
  load the full DEMO seed and exercise the API as `dapro_app` so RLS applies. `DAPRO_TEST_TESTCONTAINERS=1`
  switches to a throwaway Testcontainers PostgreSQL 16.
- Browser tests run against the demo database of the running stack. They create uniquely named records
  (`uniq(...)`) and verify them with SQL. Rerunning is safe; "Reset demo data" restores the original dataset.
- Frontend unit tests stub `fetch` (`src/test/render.tsx`) and never call a server.

## Acceptance criteria coverage (RD-001 14.3)
| AC | Evidence |
|---|---|
| AC-01 cross-college isolation | API tests (college admin RCE vs NBIT student -> 404), RLS DB test, browser check |
| AC-02 college cannot modify / see bank financials | masking tests (amounts null), no mutation endpoint, browser "Restricted" |
| AC-03 snapshot shows source and as-of | API freshness block; FreshnessBadge in UI |
| AC-04 duplicate import idempotent | `test_duplicate_sync_is_idempotent`, CSV checksum test |
| AC-05 sync failure gives STALE/UNKNOWN | `test_sync_failure_produces_unknown_not_overdue` |
| AC-06 DPD matches bank sample | DPD unit tests + DPD_MISMATCH reconciliation; **signed bank sample set not available** (OD-08) |
| AC-07 address history | lifecycle tests |
| AC-08 employment never classifies default | risk tests |
| AC-09 witness vs guarantor separation | parties tests |
| AC-10 explainable indicators | risk tests + reconstruction view |
| AC-11 field officer scope, structured outcome | field tests + mobile browser journey |
| AC-12 commitment is not payment | case tests |
| AC-13 grievance to disposition | grievance tests + browser journey |
| AC-14 exports purpose-logged | reports tests |
| AC-15 backup/restore, monitoring | backup script + restore rehearsal in DEPLOYMENT_GUIDE; client RPO/RTO undefined (OD-22) |


## Commands

```bash
docker compose run --rm --no-deps backend sh -c "ruff check app tests && pytest -q -p no:warnings"
scripts/test-migrations.sh
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
cd frontend && DAPRO_DEMO_PASSWORD=<from .env> npx playwright test             # stack running; web on 8480
cd frontend && DAPRO_WEB_URL=http://localhost:5180 npx playwright test          # against `npm run dev`
```
