"""DAPRO API application factory: middleware order, error envelope, routers."""
import json
import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import engine
from app.core.errors import BusinessError, envelope
from app.core.ids import uuid7

settings = get_settings()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name,
                "msg": record.getMessage()}
        for k in ("correlation_id", "path", "status", "ms", "method"):
            if hasattr(record, k):
                base[k] = getattr(record, k)
        if record.exc_info:
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base)


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[_handler], force=True)
log = logging.getLogger("dapro.api")

REQUESTS = Counter("dapro_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("dapro_http_request_seconds", "HTTP latency", ["method", "route"])

app = FastAPI(title="DAPRO API", version="1.0.0",
              description="DAPRO Student Loan Intelligence and Monitoring Platform. Bank data is a read-only mirror.",
              openapi_url="/api/v1/openapi.json", docs_url="/api/v1/docs", redoc_url=None)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Correlation-ID"])


@app.middleware("http")
async def correlation_and_logging(request: Request, call_next):
    corr = request.headers.get("X-Correlation-ID") or str(uuid7())
    request.state.correlation_id = corr
    start = time.perf_counter()
    response = await call_next(request)
    ms = round((time.perf_counter() - start) * 1000, 1)
    route = request.scope.get("route")
    route_path = getattr(route, "path", "unmatched")
    REQUESTS.labels(request.method, route_path, response.status_code).inc()
    LATENCY.labels(request.method, route_path).observe(ms / 1000)
    response.headers["X-Correlation-ID"] = corr
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    if request.url.path != "/api/v1/health":
        log.info("request", extra={"correlation_id": corr, "path": route_path, "status": response.status_code,
                                   "ms": ms, "method": request.method})
    return response


@app.exception_handler(BusinessError)
async def business_error(request: Request, exc: BusinessError):
    return JSONResponse(status_code=exc.status_code,
                        content=envelope(exc.code, exc.message, getattr(request.state, "correlation_id", None),
                                         exc.next_step, exc.details))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=400, content=envelope(
        "VALIDATION_FAILED", "Some fields are missing or invalid.", getattr(request.state, "correlation_id", None),
        "Correct the highlighted fields and retry.", details))


@app.exception_handler(Exception)
async def unexpected(request: Request, exc: Exception):
    corr = getattr(request.state, "correlation_id", None)
    log.exception("unhandled error", extra={"correlation_id": corr})
    return JSONResponse(status_code=500, content=envelope(
        "INTERNAL_ERROR", "Something went wrong on our side.", corr,
        "Retry shortly. If it persists, give support the correlation ID."))


@app.get("/api/v1/health", tags=["platform"])
def health():
    db_ok = True
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "environment": settings.env,
            "demo_mode": settings.env == "demo", "bank_adapter": settings.bank_adapter}


@app.get("/metrics", include_in_schema=False)
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


from app.modules.registry import register_routers  # noqa: E402

register_routers(app)
