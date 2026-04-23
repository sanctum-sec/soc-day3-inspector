from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from storage.db import init_db, get_recent_findings, get_compliance_matrix
from scheduler import start_scheduler

CHECK_ORDER = [
    "C-LIVE-001", "C-AUTH-001", "C-AUTH-002",
    "C-SCHEMA-001", "C-SCHEMA-002", "C-RATE-001",
    "C-ADMIN-001", "C-ISOLATION-001",
]
TOOL_ORDER = ["trap", "scout", "analyst", "hunter", "dispatcher"]

CHECK_LABELS = {
    "C-LIVE-001":      "GET /health → 200",
    "C-AUTH-001":      "POST /ingest no-auth → 401",
    "C-AUTH-002":      "POST /ingest bad-token → 401",
    "C-SCHEMA-001":    "POST /ingest non-JSON → 400",
    "C-SCHEMA-002":    "POST /ingest missing field → 400",
    "C-RATE-001":      "200 bursts → 429",
    "C-ADMIN-001":     "GET :8001/admin no-auth → 401",
    "C-ISOLATION-001": "GET :8000/admin → 404",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield


app = FastAPI(title="SOC Inspector", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


@app.get("/health")
async def health():
    return {"status": "ok", "tool": "inspector"}


@app.get("/findings")
async def findings(limit: int = 50):
    return await get_recent_findings(limit)


@app.get("/compliance", response_class=HTMLResponse)
async def compliance_full(request: Request):
    matrix = await get_compliance_matrix()
    recent = await get_recent_findings(20)
    return templates.TemplateResponse("compliance.html", {
        "request":      request,
        "matrix":       matrix,
        "tools":        TOOL_ORDER,
        "checks":       CHECK_ORDER,
        "check_labels": CHECK_LABELS,
        "recent":       recent,
    })


@app.get("/compliance-partial", response_class=HTMLResponse)
async def compliance_partial(request: Request):
    matrix = await get_compliance_matrix()
    recent = await get_recent_findings(20)
    return templates.TemplateResponse("compliance_partial.html", {
        "request":      request,
        "matrix":       matrix,
        "tools":        TOOL_ORDER,
        "checks":       CHECK_ORDER,
        "check_labels": CHECK_LABELS,
        "recent":       recent,
    })
