import httpx
from probes import register


@register
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    # Strip port from host and probe :8001/admin
    base = target_host.split(":")[0]
    url = f"http://{base}:8001/admin"
    try:
        r = await http_client.get(url, timeout=5.0)
        passed = r.status_code == 401
        return {
            "check_id":    "C-ADMIN-001",
            "check_label": "GET :8001/admin without auth returns 401",
            "expected":    401,
            "observed":    r.status_code,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "high",
            "notes":       "" if passed else "Admin page accessible without credentials",
        }
    except Exception as e:
        return {
            "check_id":    "C-ADMIN-001",
            "check_label": "GET :8001/admin without auth returns 401",
            "expected":    401,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "high",
            "notes":       str(e),
        }
