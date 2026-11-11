# DAPRO - Contributing Guide

## First day

1. Clone, then `cp .env.example .env` and fill the secrets (see [ENVIRONMENT_SETUP](ENVIRONMENT_SETUP.md)).
2. `docker compose up -d --build`, open http://localhost:8480 and sign in as `ravi.ops@anb.demo`.
3. Run the gates once so you know they pass on your machine (commands below).
4. Read [SYSTEM_ARCHITECTURE](SYSTEM_ARCHITECTURE.md), [SECURITY_AND_RBAC](SECURITY_AND_RBAC.md) and the
   product boundary in the README. DAPRO is a monitoring and coordination tool, not a recovery tool.

## Branches, commits and reviews

- `main` is always releasable. Work on `feature/<ticket>-<slug>`, `fix/<ticket>-<slug>` or `docs/<slug>`.
- Conventional commit subjects: `feat(grievances): ...`, `fix(loans): ...`, `docs: ...`, `test: ...`, `chore: ...`.
- One logical change per pull request. The description states the requirement IDs (FR-, UC-, AC-) it touches,
  how it was tested, and any open decision it depends on.
- At least one reviewer approval; CI (backend, frontend, secrets) must be green. No force-push to `main`.

## Gates to run before pushing

```bash
docker compose run --rm --no-deps backend sh -c "ruff check app tests && pytest -q -p no:warnings"
cd frontend && npm run typecheck && npm run lint && npm test && npm run build
cd frontend && DAPRO_DEMO_PASSWORD=<from .env> npx playwright test        # for UI or workflow changes
scripts/test-migrations.sh                                                # for any migration
```

Do not silence a failing check (no `eslint-disable`, `# noqa`, `skip`) without a comment explaining why and a
reviewer's agreement.

## Adding a feature end to end

1. **Requirement**: find the FR/UC in `docs/source` and [REQUIREMENTS_TRACEABILITY](REQUIREMENTS_TRACEABILITY.md).
   If the behaviour depends on an open decision, do not invent the rule: use a versioned policy value labelled
   `DEMO_FIXTURE` or show `NOT_CONFIGURED`, and record it in [OPEN_DECISIONS](OPEN_DECISIONS.md).
2. **Model and migration**: change `app/models`, then `alembic revision -m "<change>"`. Never edit an applied
   migration. Write a working `downgrade()`.
3. **Service**: business rules, scope checks (`core/scope.py`), state transitions, `ctx.audit(...)` for every
   consequential change, single commit.
4. **Route**: thin `api.py` with a Pydantic schema (use `Literal` for enums, length limits) and
   `Depends(require("<permission>"))`. New permissions go into `core/permissions.py` and the role matrix.
5. **Tests**: success, validation failure, missing permission, out-of-scope (404) and audit evidence.
6. **Frontend**: page under `src/features/<module>`, data through TanStack Query and `api/client.ts`, reuse
   `components/data` (DataTable, FilterBar, PageHeader, states, StatusBadge, FreshnessBadge, Money). Loading,
   empty and error states are mandatory. Add the route with a `P([...perms], ...)` guard and a nav entry.
7. **Docs**: regenerate the API inventory and data dictionary if routes or tables changed; update the
   traceability row and IMPLEMENTATION_STATUS.

## Rules that protect users and data

- Never hard-code business data, KPIs or demo records in React components; everything comes from the API.
- Never present MOCK or demo data as real. Bank data always carries source and as-of time.
- Never add covert location capture, scraping, automated adverse decisions, or contact with third parties
  without a recorded lawful basis.
- Never commit `.env`, credentials, real personal data, `node_modules`, build output, caches or logs.
- Never run destructive Docker or database commands (`docker system prune -a`, `docker volume prune`,
  `docker compose down -v`, `DROP DATABASE` on a shared database) without explicit agreement.

## Code style

- Python: ruff (config in `backend/pyproject.toml`), type hints, services return plain dicts or models,
  money with `Decimal`.
- TypeScript: strict mode, no `any`, ESLint with zero warnings, function components, Tailwind tokens from the
  design system (no ad-hoc colours).
