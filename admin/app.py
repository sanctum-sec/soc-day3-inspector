import os
import secrets
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jinja2 import Environment, FileSystemLoader

from storage.db import get_admin_stats, get_recent_findings

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "changeme")

admin_app = FastAPI(title="Inspector Admin")
_jinja = Environment(loader=FileSystemLoader("templates"), autoescape=True)
security = HTTPBasic()


def require_auth(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username.encode(), ADMIN_USER.encode())
    ok_pass = secrets.compare_digest(creds.password.encode(), ADMIN_PASS.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})
    return creds.username


@admin_app.get("/admin", response_class=HTMLResponse)
async def admin_page(_: str = Depends(require_auth)):
    stats = await get_admin_stats()
    recent = await get_recent_findings(50)
    fails = [f for f in recent if f["status"] == "FAIL"]
    unreachable = [f for f in recent if f["status"] == "UNREACHABLE"]
    html = _jinja.get_template("admin.html").render(
        stats=stats, recent=recent, fails=fails, unreachable=unreachable
    )
    return HTMLResponse(html)
