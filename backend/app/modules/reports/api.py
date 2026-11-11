"""Report and export routes."""
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.reports import service

router = APIRouter(tags=["reports"])


class RunIn(BaseModel):
    filters: dict = Field(default_factory=dict)
    page: int = 1
    size: int = 500


class ExportIn(BaseModel):
    report_code: str
    filters: dict = Field(default_factory=dict)
    purpose: str = Field(min_length=10, max_length=500)


@router.get("/reports/catalog")
def report_catalog(ctx: RequestContext = Depends(require("report:read"))):
    return service.catalog(ctx)


@router.post("/reports/{code}/run")
def run_report(code: str, body: RunIn, ctx: RequestContext = Depends(require("report:read"))):
    return service.run(ctx, code, body.filters, body.page, body.size)


@router.post("/exports", status_code=202)
def create_export(body: ExportIn, ctx: RequestContext = Depends(require("export:create"))):
    return service.create_export(ctx, body.report_code, body.filters, body.purpose)


@router.get("/exports")
def list_exports(page: int = 1, size: int = 25, ctx: RequestContext = Depends(require("export:create", "audit:read",
                                                                                         any_of=True))):
    return service.list_exports(ctx, page, size)


@router.get("/exports/{job_id}/download")
def download(job_id: UUID, ctx: RequestContext = Depends(require("export:create", "audit:read", any_of=True))):
    job = service.get_for_download(ctx, job_id)
    return FileResponse(job.storage_key, media_type="text/csv", filename=job.file_name,
                        headers={"X-Content-SHA256": job.sha256 or ""})
