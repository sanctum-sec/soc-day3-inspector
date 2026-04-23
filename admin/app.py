import os
import secrets
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from storage.db import get_admin_stats, get_recent_findings

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "changeme")

admin_app = FastAPI(title="Inspector Admin")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()


def require_auth(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username.encode(), ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(creds.password.encode(), ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return creds.username


@admin_app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, _: str = Depends(require_auth)):
    stats = await get_admin_stats()
    recent = await get_recent_findings(50)
    fails = [f for f in recent if f["status"] == "FAIL"]
    unreachable = [f for f in recent if f["status"] == "UNREACHABLE"]
    return templates.TemplateResponse("admin.html", {
        "request":     request,
        "stats":       stats,
        "recent":      recent,
        "fails":       fails,
        "unreachable": unreachable,
    })
