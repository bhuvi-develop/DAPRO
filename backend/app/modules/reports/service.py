"""Report execution and purpose-logged exports (FR-RPT-03/04, AC-14)."""
import csv
import hashlib
import io
import os
from datetime import UTC, date, datetime, time

from sqlalchemy import select

from app.common.pagination import paginate
from app.core.config import get_settings
from app.core.errors import Forbidden, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.models.platform import ExportJob
from app.modules.reports.catalog import CATALOG
from app.modules.reports.runners import RUNNERS

MAX_ROWS = 500


def iso(v):
    return v.isoformat() if v else None


def catalog(ctx) -> list[dict]:
    return [{"code": code, **spec, "allowed": all(ctx.can(p) for p in spec["required_permissions"])}
            for code, spec in CATALOG.items()]


def _spec(ctx, code):
    spec = CATALOG.get(code)
    if spec is None:
        raise NotFound("Report")
    missing = [p for p in spec["required_permissions"] if not ctx.can(p)]
    if missing:
        raise Forbidden(f"This report requires {', '.join(missing)}.")
    return spec


def _normalise(filters: dict) -> dict:
    f = {k: v for k, v in (filters or {}).items() if v not in (None, "")}
    for key, t in (("date_from", time.min), ("date_to", time.max)):
        if f.get(key):
            try:
                f[key] = datetime.combine(date.fromisoformat(str(f[key])[:10]), t, tzinfo=UTC)
            except ValueError as exc:
                raise ValidationFailed("Invalid date filter.", [{"field": key, "message": "Use YYYY-MM-DD"}]) from exc
    return f


def execute(ctx, code: str, filters: dict) -> tuple[dict, list, list]:
    spec = _spec(ctx, code)
    f = _normalise(filters)
    columns, rows = RUNNERS[code](ctx, f)
    meta = {"report_code": code, "title": spec["title"], "as_of": datetime.now(UTC).isoformat(),
            "period": {"from": iso(f.get("date_from")), "to": iso(f.get("date_to"))},
            "filters": {k: str(v) for k, v in (filters or {}).items() if v not in (None, "")},
            "source": spec["data_source"], "definition": spec["calculation_definition"],
            "generated_by_role": ctx.role, "generated_by": ctx.user_name, "organization": ctx.org_name,
            "row_count": len(rows), "data_origin": "DEMO" if get_settings().is_demo else "LIVE"}
    return meta, columns, rows


def run(ctx, code: str, filters: dict, page: int = 1, size: int = MAX_ROWS) -> dict:
    meta, columns, rows = execute(ctx, code, filters)
    size = min(max(size, 1), MAX_ROWS)
    start = (max(page, 1) - 1) * size
    meta["truncated"] = len(rows) > size
    ctx.audit("report.run", target_type="report", target_id=code, payload={"filters": meta["filters"],
                                                                          "rows": len(rows)})
    ctx.commit()
    return {"meta": meta, "columns": columns, "rows": rows[start:start + size], "total": len(rows),
            "page": max(page, 1), "size": size}


def job_row(j: ExportJob) -> dict:
    return {"id": str(j.id), "report_code": j.report_code, "title": j.title, "filters": j.filters, "purpose": j.purpose,
            "format": j.format, "status": j.status, "row_count": j.row_count, "file_name": j.file_name,
            "sha256": j.sha256, "as_of": iso(j.as_of), "error": j.error, "requested_by": str(j.requested_by),
            "created_at": iso(j.created_at), "completed_at": iso(j.completed_at)}


def create_export(ctx, code: str, filters: dict, purpose: str) -> dict:
    spec = _spec(ctx, code)
    if not purpose or len(purpose.strip()) < 10:
        raise ValidationFailed("State the purpose of this export.", [{"field": "purpose", "message": "Minimum 10 characters"}])
    job = ExportJob(id=uuid7(), tenant_id=ctx.tenant_id, report_code=code, title=spec["title"], filters=filters or {},
                    purpose=purpose.strip(), status="QUEUED", requested_by=ctx.user_id)
    ctx.db.add(job)
    ctx.audit("export.created", target_type="export", target_id=job.id, target_label=spec["title"],
              purpose=purpose.strip()[:40], payload={"report_code": code, "filters": filters or {},
                                                     "purpose": purpose.strip()})
    ctx.commit()
    from app.workers.tasks_financial import export_report

    export_report.delay(str(ctx.tenant_id), str(job.id))
    ctx.db.refresh(job)
    return job_row(job)


def _storage_path(tenant_id, job_id) -> str:
    d = os.path.join(get_settings().storage_dir, "exports", str(tenant_id))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{job_id}.csv")


def execute_export(db, job_id) -> None:
    """Worker side: rebuild the requester context so the export uses exactly their scope and masking."""
    from app.core.authz import build_context
    from app.models.iam import User

    job = db.get(ExportJob, job_id)
    if job is None or job.status not in ("QUEUED", "FAILED"):
        return
    job.status = "RUNNING"
    db.flush()
    try:
        ctx = build_context(db, db.get(User, job.requested_by))
        ctx.correlation_id = str(job.id)
        meta, columns, rows = execute(ctx, job.report_code, job.filters)
        buf = io.StringIO()
        w = csv.writer(buf)
        for k in ("title", "as_of", "source", "definition", "generated_by", "generated_by_role", "data_origin"):
            w.writerow([f"# {k}", meta[k]])
        w.writerow(["# filters", meta["filters"]])
        w.writerow(["# purpose", job.purpose])
        w.writerow([c["label"] for c in columns])
        for r in rows:
            w.writerow(["" if r.get(c["key"]) is None else r.get(c["key"]) for c in columns])
        data = buf.getvalue().encode("utf-8")
        path = _storage_path(job.tenant_id, job.id)
        with open(path, "wb") as fh:
            fh.write(data)
        job.sha256, job.storage_key, job.row_count = hashlib.sha256(data).hexdigest(), path, len(rows)
        job.file_name = f"{job.report_code.lower()}-{datetime.now(UTC):%Y%m%d-%H%M}.csv"
        job.status, job.as_of, job.completed_at = "COMPLETED", datetime.now(UTC), datetime.now(UTC)
    except Exception as exc:  # recorded on the job; never silently lost
        job.status, job.error = "FAILED", str(exc)[:500]
        db.flush()
        raise


def list_exports(ctx, page, size) -> dict:
    stmt = select(ExportJob).order_by(ExportJob.created_at.desc())
    if not ctx.can("audit:read"):
        stmt = stmt.where(ExportJob.requested_by == ctx.user_id)
    rows, total, page, size = paginate(ctx.db, stmt, page, size)
    return {"items": [job_row(j) for j in rows], "total": total, "page": page, "size": size}


def get_for_download(ctx, job_id) -> ExportJob:
    job = ctx.db.get(ExportJob, job_id)
    if job is None or (job.requested_by != ctx.user_id and not ctx.can("audit:read")):
        raise NotFound("Export")
    if job.status != "COMPLETED" or not job.storage_key or not os.path.exists(job.storage_key):
        raise ValidationFailed("This export is not ready.", next_step="Wait for the export to complete, then retry.")
    ctx.audit("export.downloaded", target_type="export", target_id=job.id, target_label=job.title,
              payload={"sha256": job.sha256, "requested_by": str(job.requested_by)})
    ctx.commit()
    return job
