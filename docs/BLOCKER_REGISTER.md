# DAPRO - Blocker Register

Audit and resolution log for the 2026-11-06 rebuild session. "Verified" means the named check was run after the
fix and passed.

## Resolved

| ID | Area | Blocker | Root cause | Resolution | Verified by |
|---|---|---|---|---|---|
| BLK-01 | Frontend | `tsc` and ESLint failed: unused `Badge` import in `features/admin/IntegrationsPage.tsx` | Leftover import | Import removed | `npm run typecheck`, `npm run lint` (0 warnings) |
| BLK-02 | Frontend | 7 placeholder pages ("Module under construction"): Policies, Grievances, Grievance Detail, Portal Home, Portal Messages, Portal Profile, Portal Grievances | Implementation interrupted in the previous session | Implemented against the existing APIs: policy versions with maker-checker; grievance queue (filters, search, sort, pagination, create), detail (assign, respond, internal notes, transitions, correction approval, timeline); portal loan overview with freshness, profile with address and employment updates, requests (raise, track, read responses), messages | `grep PLACEHOLDER` empty; unit tests; e2e grievances/portal/admin specs |
| BLK-03 | Docker | Compose project was `dapro-ent`, services `db/api/worker/web`; several older DAPRO stacks exist on the machine | Earlier naming | Project renamed `dapro-platform`; services `postgres, redis, backend, celery-worker, celery-beat, frontend`; required secrets enforced with `${VAR:?}`; health checks incl. frontend `/healthz`; memory limits; 127.0.0.1-only ports; separate single beat scheduler (was `worker -B`) | `docker compose config`, stack up and healthy, old stacks untouched |
| BLK-04 | Background jobs | Celery worker and beat crash-looped: `kombu.exceptions.VersionMismatch: Redis transport requires redis-py>=6.1` | `kombu` not pinned; a new release required a newer redis-py than the pinned 5.2.1. Masked in tests by eager mode | Pinned `kombu==5.4.2`, `billiard==4.2.1`, `vine==5.1.0`; added `backend/constraints.txt` (full transitive lock) used by Dockerfile and CI | Worker `ready`, beat schedules, `dapro.comms.dispatch` succeeded (9 messages), export journey e2e passed |
| BLK-05 | Frontend | App crashed with React Router's raw error page: "A component suspended while responding to synchronous input" | Lazy `PortalLayout`, Login and Accept-invite routes had no Suspense boundary; router had no error element | Every lazy route wrapped in Suspense; `v7_startTransition` and `v7_relativeSplatPath` enabled; `RouteError` page | e2e portal and grievance journeys pass from a cold load |
| BLK-06 | Testing | Playwright suite could not run: `__dirname is not defined in ES module scope` | CommonJS global in an ESM helper | `fileURLToPath(import.meta.url)` | `npx playwright test` runs |
| BLK-07 | Testing | Login helper never matched the password field | Label text is "Password*" (required marker) with exact match | Target `#password` | All e2e logins succeed |
| BLK-08 | Testing | 5 of 7 planned e2e specs missing (students/admin/operations/portal/mobile), demo borrower hard-coded to a non-existent user | Interrupted session; seed generates borrowers | Added grievances, portal, admin, operations, mobile specs; borrowers looked up from the database | 24/24 e2e pass |
| BLK-09 | Testing | No frontend unit tests (Vitest configured, zero tests) | Not written | 15 tests: API client (token, error mapping, refresh/retry, session clear), formatting, portal grievance form validation and submission, policy maker-checker UI, permission guard | `npm test` |
| BLK-10 | Backend validation | Grievance `channel`, `priority`, `visibility` and transition `to` accepted any string | Plain `str` fields | Pydantic `Literal` enums and length limit | `test_grievance_inputs_are_constrained` |
| BLK-11 | Security | API would start in production with the public default JWT secret, default DB passwords, non-Secure cookies or MOCK providers | No configuration guard | Settings validator refuses these outside demo/development/test | `test_production_refuses_insecure_defaults` |
| BLK-12 | UI/API consistency | Policy page offered "Reject" on the maker's own draft; the API (correctly, BR-12) refused it | UI rule differed from server rule | Both actions disabled for the maker with an explanation; recorded as OD-28 | Unit test + admin e2e |
| BLK-13 | Docs / repo | No root README; docs referenced the old OneDrive path and old service names; no `.gitattributes` | Earlier session | README, 15 documents, baseline note, LF line endings enforced for scripts | Review |
| BLK-14 | Scripts | `test-migrations.sh`, `backup.sh`, `restore-check.sh` read passwords from an unset shell variable and used old service names | Not updated | Scripts source `.env` and use `postgres`/`backend` | `docker compose config`; migration check run (see TESTING_AND_VALIDATION) |
| BLK-15 | Frontend Docker build | `npm ci` crashed with "Exit handler never called" after registry timeouts | Flaky registry access | BuildKit npm cache mount and npm retry settings in `frontend/Dockerfile` | See EXT-01 |
| BLK-16 | Tests | Order-dependent failure in `test_risk` reported in the previous checkpoint | Fixed previously, never re-run | Full suite re-run | pytest full suite passes |

## Open - environment or external (not fixable in code)

| ID | Blocker | Impact | Owner / next step |
|---|---|---|---|
| EXT-01 | On the build machine, the Docker Desktop VM had no outbound HTTPS to PyPI, npm or Docker Hub on 2026-11-06 (TLS handshake timeouts; the host itself reached PyPI) | `docker compose build` could not produce fresh images locally. Verification used the previously built backend image with the pinned `kombu` installed from a host-downloaded wheel (local only), and the frontend was exercised through the Vite dev server against the same backend | Rebuild both images on a machine with registry access: `docker compose build --no-cache && docker compose up -d`, then re-run the e2e suite against port 8480 |
| EXT-02 | No live bank API, SMS or email provider | Bank data, SMS and email are MOCK and labelled MOCK | Client decisions OD-06, OD-16 and credentials |
| EXT-03 | No signed bank DPD sample set | AC-06 cannot be certified against bank-calculated DPD | Bank to provide a test set (OD-08) |
| EXT-04 | Draft requirements | Role matrix, SLA, risk thresholds, retention, hosting are demo fixtures | Client review of RD-001 and OD register |
| EXT-05 | No pilot baseline data | UC-38 improvement claims cannot be computed | Client to provide baseline metrics (RD 3.3) |
