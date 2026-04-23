import os, httpx
from probes import register


@register
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    url = f"http://{target_host}/ingest"
    token = os.environ.get("SOC_PROTOCOL_TOKEN", "")
    try:
        r = await http_client.post(
            url,
            content=b"<html>not json</html>",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/html",
            },
            timeout=5.0,
        )
        passed = r.status_code == 400
        return {
            "check_id":    "C-SCHEMA-001",
            "check_label": "POST /ingest with non-JSON body returns 400",
            "expected":    400,
            "observed":    r.status_code,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "medium",
            "notes":       "" if passed else f"Accepted non-JSON payload — schema validation missing",
        }
    except Exception as e:
        return {
            "check_id":    "C-SCHEMA-001",
            "check_label": "POST /ingest with non-JSON body returns 400",
            "expected":    400,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "medium",
            "notes":       str(e),
        }
