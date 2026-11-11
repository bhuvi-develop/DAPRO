"""Student routes (Module 02)."""
from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.students import imports, profile, service
from app.modules.students.schemas import DuplicateResolve, StudentCreate, StudentPatch
from app.workers.tasks_core import process_student_csv

router = APIRouter(tags=["students"])


@router.get("/students")
def list_students(page: int = 1, size: int = 25, q: str | None = None, college_org_id: str | None = None,
                  lifecycle_status: str | None = None, verification_status: str | None = None,
                  completion_below: int | None = Query(None, ge=0, le=101), has_loan: bool | None = None,
                  cohort: int | None = None, created_after: str | None = None, sort: str | None = None,
                  ctx: RequestContext = Depends(require("student:read"))):
    f = {"q": q, "college_org_id": college_org_id, "lifecycle_status": lifecycle_status,
         "verification_status": verification_status, "completion_below": completion_below, "has_loan": has_loan,
         "cohort": cohort, "created_after": created_after, "sort": sort}
    return service.list_students(ctx, f, page, size)


@router.post("/students", status_code=201)
def create_student(body: StudentCreate, ctx: RequestContext = Depends(require("student:write"))):
    s = service.create_student(ctx, body)
    return service.serialize(ctx, s, service.org_names(ctx.db), 0)


@router.get("/students/duplicates")
def duplicates(status: str = "OPEN", ctx: RequestContext = Depends(require("student:merge"))):
    return service.list_duplicates(ctx, status)


@router.post("/students/duplicates/{dup_id}/resolve")
def resolve_duplicate(dup_id: str, body: DuplicateResolve, ctx: RequestContext = Depends(require("student:merge"))):
    return service.resolve_duplicate(ctx, dup_id, body.decision, body.notes)


@router.get("/students/imports/template", response_class=PlainTextResponse)
def import_template(ctx: RequestContext = Depends(require("student:import"))):
    return PlainTextResponse(imports.TEMPLATE, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=dapro-student-import-template.csv"})


@router.get("/students/imports")
def list_imports(page: int = 1, size: int = 25, ctx: RequestContext = Depends(require("student:import"))):
    return imports.list_batches(ctx, page, size)


@router.post("/students/imports", status_code=202)
def upload_import(file: UploadFile = File(...), ctx: RequestContext = Depends(require("student:import"))):
    b = imports.upload(ctx, file.file.read(), file.filename or "upload.csv")
    process_student_csv.delay(str(b.id), str(ctx.tenant_id))
    ctx.db.expire_all()
    return imports.batch_dict(imports.get_batch(ctx, b.id))


@router.get("/students/imports/{batch_id}")
def get_import(batch_id: str, ctx: RequestContext = Depends(require("student:import"))):
    return imports.batch_dict(imports.get_batch(ctx, batch_id))


@router.post("/students/imports/{batch_id}/apply")
def apply_import(batch_id: str, ctx: RequestContext = Depends(require("student:import"))):
    return imports.batch_dict(imports.apply(ctx, batch_id))


@router.get("/students/{student_id}")
def get_student(student_id: str, ctx: RequestContext = Depends(require("student:read"))):
    from app.modules.students.repo import get_scoped
    return service.serialize(ctx, get_scoped(ctx, student_id), service.org_names(ctx.db))


@router.get("/students/{student_id}/profile")
def student_profile(student_id: str, ctx: RequestContext = Depends(require("student:read"))):
    return profile.build_profile(ctx, student_id)


@router.patch("/students/{student_id}")
def update_student(student_id: str, body: StudentPatch, if_match: str | None = Header(None),
                   ctx: RequestContext = Depends(require("student:write"))):
    version = int(if_match.strip('"')) if if_match and if_match.strip('"').isdigit() else None
    s = service.update_student(ctx, student_id, version, body)
    return service.serialize(ctx, s, service.org_names(ctx.db))


@router.get("/students/{student_id}/history")
def field_history(student_id: str, ctx: RequestContext = Depends(require("student:read"))):
    return service.field_history(ctx, student_id)
