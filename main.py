from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from storage.db import init_db, get_recent_findings, get_compliance_matrix
from scheduler import start_scheduler

_jinja = Environment(loader=FileSystemLoader("templates"), autoescape=True)

CHECK_ORDER = [
    "C-LIVE-001", "C-AUTH-001", "C-AUTH-002",
    "C-SCHEMA-001", "C-SCHEMA-002", "C-RATE-001",
    "C-ADMIN-001", "C-ISOLATION-001",
]
TOOL_ORDER = ["trap", "scout", "analyst", "hunter", "dispatcher"]

# Short technical label shown in the check column header
CHECK_LABELS = {
    "C-LIVE-001":      "Service is running",
    "C-AUTH-001":      "Rejects unauthenticated requests",
    "C-AUTH-002":      "Validates token value, not just presence",
    "C-SCHEMA-001":    "Rejects non-JSON input",
    "C-SCHEMA-002":    "Validates required envelope fields",
    "C-RATE-001":      "Rate limiting is active",
    "C-ADMIN-001":     "Admin page requires credentials",
    "C-ISOLATION-001": "Admin not exposed on public port",
}

# Plain-English description shown as subtitle in the check column
CHECK_DESC = {
    "C-LIVE-001":
        "GET /health → 200. The service responded. If this fails, nothing else can be checked.",
    "C-AUTH-001":
        "POST /ingest with no token → 401. Anyone without credentials must be turned away. "
        "A 200 here means the pipeline accepts unauthenticated writes — data integrity risk.",
    "C-AUTH-002":
        "POST /ingest with wrong token → 401. The token value must be verified, not just its presence. "
        "A 200 here means any string in the header is accepted.",
    "C-SCHEMA-001":
        "POST /ingest with HTML body → 400. Non-JSON input must be rejected before processing. "
        "A 200 here means malformed data could enter the pipeline.",
    "C-SCHEMA-002":
        "POST /ingest with incomplete JSON → 400. Required protocol fields must all be present. "
        "A 200 here means downstream tools may receive incomplete events and crash or misfire.",
    "C-RATE-001":
        "200 rapid requests → at least one 429. Rate limiting must cut off floods. "
        "Absence of 429 means an adversary could overwhelm the pipeline or hide real events in noise.",
    "C-ADMIN-001":
        "GET :8001/admin with no credentials → 401. The admin page must require a password. "
        "A 200 here means operational data is publicly visible.",
    "C-ISOLATION-001":
        "GET :8000/admin → 404. Admin must not exist on the public port. "
        "A 200 here means admin is reachable by anyone who can reach the service.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield


app = FastAPI(title="SOC Inspector", lifespan=lifespan)


def _render(template_name: str, **ctx) -> HTMLResponse:
    html = _jinja.get_template(template_name).render(**ctx)
    return HTMLResponse(html)


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
    return _render("compliance.html",
        matrix=matrix, tools=TOOL_ORDER, checks=CHECK_ORDER,
        check_labels=CHECK_LABELS, check_desc=CHECK_DESC, recent=recent)


@app.get("/compliance-partial", response_class=HTMLResponse)
async def compliance_partial(request: Request):
    matrix = await get_compliance_matrix()
    recent = await get_recent_findings(20)
    return _render("compliance_partial.html",
        matrix=matrix, tools=TOOL_ORDER, checks=CHECK_ORDER,
        check_labels=CHECK_LABELS, check_desc=CHECK_DESC, recent=recent)
