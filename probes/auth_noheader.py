import uuid, datetime, httpx
from probes import register


def _payload():
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "telemetry",
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": "inspector",
        "severity": "low",
    }


@register
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    url = f"http://{target_host}/ingest"
    try:
        r = await http_client.post(url, json=_payload(), timeout=5.0)
        passed = r.status_code == 401
        return {
            "check_id":    "C-AUTH-001",
            "check_label": "POST /ingest with no Authorization returns 401",
            "expected":    401,
            "observed":    r.status_code,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "high",
            "notes":       "" if passed else f"Accepted unauthenticated request — violates soc-protocol §7.1",
        }
    except Exception as e:
        return {
            "check_id":    "C-AUTH-001",
            "check_label": "POST /ingest with no Authorization returns 401",
            "expected":    401,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "high",
            "notes":       str(e),
        }
