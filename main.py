from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
import asyncio, os

from storage.db import init_db, get_recent_findings, get_compliance_matrix
from scheduler import start_scheduler, run_regular_probes, _last_run

_jinja = Environment(loader=FileSystemLoader("templates"), autoescape=True)

CHECK_ORDER = [
    "C-LIVE-001", "C-AUTH-001", "C-AUTH-002",
    "C-SCHEMA-001", "C-SCHEMA-002", "C-RATE-001",
    "C-ADMIN-001", "C-ISOLATION-001",
]
TOOL_ORDER = ["trap", "scout", "analyst", "hunter", "dispatcher"]

TOOL_NAMES_UA = {
    "trap":       "★ Пастка",
    "scout":      "★ Розвідник",
    "analyst":    "★ Аналітик",
    "hunter":     "★ Мисливець",
    "dispatcher": "★ Диспетчер",
}

CHECK_LABELS = {
    "C-LIVE-001":      "Сервіс працює",
    "C-AUTH-001":      "Відхиляє неавтентифіковані запити",
    "C-AUTH-002":      "Перевіряє значення токена, а не лише його наявність",
    "C-SCHEMA-001":    "Відхиляє дані не у форматі JSON",
    "C-SCHEMA-002":    "Перевіряє наявність обов'язкових полів конверта",
    "C-RATE-001":      "Обмеження частоти запитів активне",
    "C-ADMIN-001":     "Сторінка адміністратора захищена паролем",
    "C-ISOLATION-001": "Адмін-панель недоступна на публічному порту",
}

CHECK_DESC = {
    "C-LIVE-001":
        "GET /health → 200. Сервіс відповів. "
        "Якщо ця перевірка не проходить — жодну іншу виконати неможливо.",
    "C-AUTH-001":
        "POST /ingest без токена → 401. Усі запити без облікових даних мають відхилятися. "
        "Код 200 тут означає, що pipeline приймає неавтентифіковані записи — ризик цілісності даних.",
    "C-AUTH-002":
        "POST /ingest з невірним токеном → 401. Значення токена має перевірятися, а не лише його наявність. "
        "Код 200 тут означає, що будь-який рядок у заголовку Authorization приймається.",
    "C-SCHEMA-001":
        "POST /ingest з HTML-тілом → 400. Дані не у форматі JSON мають відхилятися до обробки. "
        "Код 200 тут означає, що некоректні дані можуть потрапити в pipeline.",
    "C-SCHEMA-002":
        "POST /ingest з неповним JSON → 400. Усі обов'язкові поля протоколу мають бути присутні. "
        "Код 200 тут означає, що downstream-інструменти можуть отримати неповні події та збоїти.",
    "C-RATE-001":
        "200 швидких запитів → хоча б один 429. Обмеження частоти має зупиняти потоки запитів. "
        "Відсутність 429 означає, що зловмисник може перевантажити pipeline або приховати реальні події в шумі.",
    "C-ADMIN-001":
        "GET :8001/admin без облікових даних → 401. Сторінка адміністратора має вимагати пароль. "
        "Код 200 тут означає, що оперативні дані публічно доступні.",
    "C-ISOLATION-001":
        "GET :8000/admin → 404. Адмін-панель не повинна існувати на публічному порту. "
        "Код 200 тут означає, що адмін-панель доступна будь-кому, хто може зв'язатися з сервісом.",
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
        tool_names_ua=TOOL_NAMES_UA,
        check_labels=CHECK_LABELS, check_desc=CHECK_DESC, recent=recent)


@app.get("/compliance-partial", response_class=HTMLResponse)
async def compliance_partial(request: Request):
    matrix = await get_compliance_matrix()
    recent = await get_recent_findings(20)
    return _render("compliance_partial.html",
        matrix=matrix, tools=TOOL_ORDER, checks=CHECK_ORDER,
        tool_names_ua=TOOL_NAMES_UA,
        check_labels=CHECK_LABELS, check_desc=CHECK_DESC, recent=recent)


_PROBE_TOKEN = os.environ.get("SOC_PROTOCOL_TOKEN", "")

@app.post("/findings/refresh")
async def force_refresh(authorization: str = Header(default="")):
    """Clear the rate-limiter and immediately re-run all probes.
    Requires the shared SOC bearer token so any team can trigger it."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token or token != _PROBE_TOKEN:
        raise HTTPException(status_code=401, detail="Valid bearer token required")
    _last_run.clear()
    asyncio.create_task(run_regular_probes())
    return {"status": "refresh triggered", "message": "Probes re-running now. Results appear in ~10 seconds."}
