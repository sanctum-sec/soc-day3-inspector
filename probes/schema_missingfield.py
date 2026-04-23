import os, httpx
from probes import register


@register
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    url = f"http://{target_host}/ingest"
    token = os.environ.get("SOC_PROTOCOL_TOKEN", "")
    # Valid auth, valid JSON, but only one field — missing schema_version,
    # event_id, timestamp, producer, severity
    incomplete = {"event_type": "telemetry"}
    try:
        r = await http_client.post(
            url,
            json=incomplete,
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        passed = r.status_code == 400
        return {
            "check_id":    "C-SCHEMA-002",
            "check_label": "POST /ingest with missing required fields returns 400",
            "expected":    400,
            "observed":    r.status_code,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "medium",
            "notes":       "" if passed else "Accepted envelope missing required fields — schema validation missing",
        }
    except Exception as e:
        return {
            "check_id":    "C-SCHEMA-002",
            "check_label": "POST /ingest with missing required fields returns 400",
            "expected":    400,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "medium",
            "notes":       str(e),
        }
