import httpx
from probes import register


@register
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    # Admin must NOT be reachable on the public app port (8000)
    url = f"http://{target_host}/admin"
    try:
        r = await http_client.get(url, timeout=5.0)
        passed = r.status_code == 404
        return {
            "check_id":    "C-ISOLATION-001",
            "check_label": "GET :8000/admin returns 404 (admin not on app port)",
            "expected":    404,
            "observed":    r.status_code,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "high",
            "notes":       "" if passed else f"Admin route exposed on public port 8000 — should only be on port 8001",
        }
    except Exception as e:
        return {
            "check_id":    "C-ISOLATION-001",
            "check_label": "GET :8000/admin returns 404 (admin not on app port)",
            "expected":    404,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "high",
            "notes":       str(e),
        }
