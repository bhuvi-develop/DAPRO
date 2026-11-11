"""Generate docs/database/DATA_DICTIONARY.md and docs/api/API_INVENTORY.md from the live code.

Run inside the api container:  python scripts/gen_docs.py /docs
Generated from SQLAlchemy metadata and the FastAPI OpenAPI schema so the documents cannot drift from the code.
"""
import sys
from pathlib import Path

from app.models import RLS_TABLES, Base

APPEND_ONLY = {"audit_events", "repayment_transactions", "loan_snapshots", "risk_reviews", "student_field_changes",
               "case_events", "grievance_events"}


def data_dictionary() -> str:
    out = ["# DAPRO - Data Dictionary", "",
           "Generated from SQLAlchemy metadata (`backend/scripts/gen_docs.py`). Identifiers are UUIDv7. Money is "
           "NUMERIC(18,2) INR. Timestamps are UTC (timestamptz).", "",
           "Legend: RLS = row-level security tenant isolation; APPEND-ONLY = UPDATE/DELETE revoked from dapro_app "
           "(audit_events additionally protected by a trigger for every role).", ""]
    for t in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        flags = []
        if t.name in RLS_TABLES:
            flags.append("RLS")
        if t.name in APPEND_ONLY:
            flags.append("APPEND-ONLY")
        out.append(f"## {t.name}" + (f"  `{' '.join(flags)}`" if flags else ""))
        doc = (t.info or {}).get("doc")
        if doc:
            out.append(doc)
        out += ["", "| Column | Type | Null | Key / default |", "|---|---|---|---|"]
        for c in t.columns:
            keys = []
            if c.primary_key:
                keys.append("PK")
            for fk in c.foreign_keys:
                keys.append(f"FK {fk.target_fullname}")
            if c.server_default is not None:
                keys.append("default " + str(getattr(c.server_default, "arg", "")).replace("|", "/")[:30])
            out.append(f"| {c.name} | {str(c.type).replace('|', '/')} | {'yes' if c.nullable else 'no'} | {', '.join(keys)} |")
        uniques = [", ".join(col.name for col in con.columns) for con in t.constraints
                   if con.__class__.__name__ == "UniqueConstraint"]
        if uniques:
            out.append("")
            out.append("Unique: " + "; ".join(f"({u})" for u in uniques))
        idx = [i.name for i in t.indexes]
        if idx:
            out.append("Indexes: " + ", ".join(sorted(idx)))
        out.append("")
    return "\n".join(out)


def api_inventory() -> str:
    from fastapi.routing import APIRoute

    from app.main import app
    from app.modules.auth.api import PUBLIC_PATHS

    rows = []
    for r in app.routes:
        if not isinstance(r, APIRoute):
            continue
        perms = []
        for d in r.dependant.dependencies:
            p = getattr(d.call, "__dapro_permission__", None)
            if p:
                perms.extend(p)
        perm = ", ".join(perms) if perms else ("public" if r.path in PUBLIC_PATHS or r.path.endswith("/health") else "-")
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            rows.append((r.path, m, perm, (r.summary or r.name).replace("_", " "), r.tags[0] if r.tags else ""))
    rows.sort(key=lambda x: (x[4], x[0], x[1]))
    out = ["# DAPRO - API Inventory", "",
           "Generated from the FastAPI application (`backend/scripts/gen_docs.py`). Base path `/api/v1`. "
           "Interactive OpenAPI: `/api/v1/docs`, schema: `/api/v1/openapi.json`.", "",
           "Conventions: Bearer access token; X-Correlation-ID echoed; error envelope "
           "`{error:{code,message,next_step,correlation_id,details}}`; list endpoints return "
           "`{items,total,page,size}`; money as decimal strings; financial blocks carry `freshness`.", "",
           f"Total operations: {len(rows)}", "", "| Module | Method | Path | Permission | Operation |", "|---|---|---|---|---|"]
    for path, m, perm, name, tag in rows:
        out.append(f"| {tag} | {m} | `{path}` | {perm} | {name} |")
    return "\n".join(out)


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "../docs")
    (root / "database").mkdir(parents=True, exist_ok=True)
    (root / "api").mkdir(parents=True, exist_ok=True)
    (root / "database" / "DATA_DICTIONARY.md").write_text(data_dictionary(), encoding="utf-8")
    (root / "api" / "API_INVENTORY.md").write_text(api_inventory(), encoding="utf-8")
    print("docs generated")
