import httpx
from probes import register


@register
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    url = f"http://{target_host}/health"
    try:
        r = await http_client.get(url, timeout=3.0)
        passed = r.status_code == 200
        return {
            "check_id":    "C-LIVE-001",
            "check_label": "GET /health returns 200",
            "expected":    200,
            "observed":    r.status_code,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "high",
            "notes":       "" if passed else f"Got {r.status_code}",
        }
    except Exception as e:
        return {
            "check_id":    "C-LIVE-001",
            "check_label": "GET /health returns 200",
            "expected":    200,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "high",
            "notes":       str(e),
        }
