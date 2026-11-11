"""College student CSV import: upload -> VALIDATED (row errors) -> APPLIED (INT-COL-01, INT-COM-04)."""
import csv
import hashlib
import io
import os
import re
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.common.pagination import paginate
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.errors import BusinessError, NotFound, ValidationFailed
from app.models.loans import ImportBatch
from app.models.students import Student
from app.modules.students.schemas import StudentCreate

COLUMNS = ["college_student_id", "first_name", "last_name", "dob", "email", "mobile", "programme", "course",
           "cohort_year"]
TEMPLATE = ",".join(COLUMNS) + "\nNBIT26X0001,Asha,Raman,2007-04-12,asha.raman@mail.demo,+919876543210,B.E.,Computer Science and Engineering,2026\n"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def batch_dict(b: ImportBatch) -> dict:
    return {"id": str(b.id), "kind": b.kind, "source": b.source, "file_name": b.file_name, "status": b.status,
            "total_rows": b.total_rows, "valid_rows": b.valid_rows, "applied_rows": b.applied_rows,
            "error_rows": b.error_rows, "duplicate_rows": b.duplicate_rows, "errors": b.errors[:200],
            "summary": b.summary, "checksum": b.checksum, "created_at": b.created_at, "finished_at": b.finished_at,
            "uploaded_by": str(b.uploaded_by) if b.uploaded_by else None,
            "approved_by": str(b.approved_by) if b.approved_by else None}


def upload(ctx: RequestContext, content: bytes, filename: str) -> ImportBatch:
    if not ctx.is_college:
        raise BusinessError("FORBIDDEN", "Student imports are performed by the owning college.", None, 403)
    s = get_settings()
    if len(content) > s.max_upload_mb * 1024 * 1024:
        raise ValidationFailed(f"File is larger than {s.max_upload_mb} MB.")
    if not filename.lower().endswith(".csv"):
        raise ValidationFailed("Only .csv files are accepted.", [{"field": "file", "message": "Use the CSV template"}])
    checksum = hashlib.sha256(content).hexdigest()
    prior = ctx.db.execute(select(ImportBatch).where(ImportBatch.checksum == checksum,
                                                     ImportBatch.kind == "STUDENT_CSV",
                                                     ImportBatch.status != "FAILED")).scalar()
    if prior:
        raise BusinessError("DUPLICATE_IMPORT", "This exact file was already imported.",
                            "Open the earlier import instead of uploading again.", 409,
                            [{"batch_id": str(prior.id), "status": prior.status}])
    b = ImportBatch(tenant_id=ctx.tenant_id, org_id=ctx.org_id, kind="STUDENT_CSV", source="CSV_UPLOAD",
                    file_name=os.path.basename(filename)[:200], checksum=checksum, status="QUEUED",
                    uploaded_by=ctx.user_id, correlation_id=ctx.correlation_id, data_origin="LIVE")
    ctx.db.add(b)
    ctx.db.flush()
    folder = os.path.join(s.storage_dir, "imports", str(ctx.tenant_id))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{b.id}.csv")
    with open(path, "wb") as fh:
        fh.write(content)
    b.storage_key = path
    ctx.audit("import.uploaded", target_type="import_batch", target_id=b.id, target_label=b.file_name,
              payload={"kind": "STUDENT_CSV", "checksum": checksum})
    ctx.commit()
    return b


def validate_batch(db, b: ImportBatch) -> None:
    b.status, b.started_at = "RUNNING", datetime.now(UTC)
    with open(b.storage_key, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(io.StringIO(fh.read()))
    missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        b.status, b.finished_at = "FAILED", datetime.now(UTC)
        b.errors = [{"row": None, "field": None, "message": "Missing columns: " + ", ".join(missing)}]
        return
    existing = set(db.execute(select(Student.college_student_id).where(Student.college_org_id == b.org_id)).scalars())
    seen, errors, valid, dup, total = set(), [], 0, 0, 0
    for n, row in enumerate(reader, start=2):
        total += 1
        row_errs = [{"row": n, "field": c, "message": "Required"} for c in COLUMNS if not (row.get(c) or "").strip()]
        try:
            date.fromisoformat((row.get("dob") or "").strip())
        except ValueError:
            row_errs.append({"row": n, "field": "dob", "message": "Use YYYY-MM-DD"})
        if row.get("email") and not EMAIL.match(row["email"].strip()):
            row_errs.append({"row": n, "field": "email", "message": "Invalid email"})
        if not (row.get("cohort_year") or "").strip().isdigit():
            row_errs.append({"row": n, "field": "cohort_year", "message": "Must be a year"})
        sid = (row.get("college_student_id") or "").strip()
        if sid in existing or sid in seen:
            dup += 1
        seen.add(sid)
        if row_errs:
            errors.extend(row_errs)
        else:
            valid += 1
    b.total_rows, b.valid_rows, b.duplicate_rows = total, valid, dup
    b.error_rows = len({e["row"] for e in errors})
    b.errors = errors
    b.status, b.finished_at = "VALIDATED", datetime.now(UTC)


def get_batch(ctx: RequestContext, batch_id) -> ImportBatch:
    b = ctx.db.get(ImportBatch, batch_id)
    if b is None or b.kind != "STUDENT_CSV" or (ctx.org_type != "PLATFORM" and b.org_id != ctx.org_id):
        raise NotFound("Import batch")
    return b


def list_batches(ctx: RequestContext, page: int, size: int) -> dict:
    stmt = select(ImportBatch).where(ImportBatch.kind == "STUDENT_CSV", ImportBatch.org_id == ctx.org_id) \
        .order_by(ImportBatch.created_at.desc())
    rows, total, page, size = paginate(ctx.db, stmt, page, size)
    return {"items": [batch_dict(b) for b in rows], "total": total, "page": page, "size": size}


def apply(ctx: RequestContext, batch_id) -> ImportBatch:
    from app.modules.students.service import create_student

    b = get_batch(ctx, batch_id)
    if b.status != "VALIDATED":
        raise BusinessError("INVALID_STATE", f"Import is {b.status}; only VALIDATED imports can be applied.",
                            "Upload a corrected file.", 409)
    bad_rows = {e["row"] for e in b.errors}
    with open(b.storage_key, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(io.StringIO(fh.read())))
    applied = dup = 0
    for n, row in enumerate(rows, start=2):
        if n in bad_rows:
            continue
        body = StudentCreate(college_org_id=str(b.org_id), college_student_id=row["college_student_id"].strip(),
                             first_name=row["first_name"].strip(), last_name=row["last_name"].strip(),
                             dob=date.fromisoformat(row["dob"].strip()), email=row["email"].strip() or None,
                             mobile=(row.get("mobile") or "").strip() or None, programme=row["programme"].strip(),
                             course=row["course"].strip(), cohort_year=int(row["cohort_year"]),
                             confirm_not_duplicate=True)
        try:
            with ctx.db.begin_nested():
                create_student(ctx, body, source="COLLEGE_IMPORT", batch_id=b.id, commit=False)
            applied += 1
        except BusinessError as exc:
            if exc.code != "DUPLICATE_STUDENT_ID":
                raise
            dup += 1
    b.applied_rows, b.duplicate_rows = applied, dup
    b.status, b.approved_by, b.approved_at = "APPLIED", ctx.user_id, datetime.now(UTC)
    b.summary = {"created": applied, "skipped_duplicates": dup, "rejected_rows": len(bad_rows)}
    ctx.audit("import.applied", target_type="import_batch", target_id=b.id, target_label=b.file_name,
              payload=b.summary)
    ctx.commit()
    return b
