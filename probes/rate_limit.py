import asyncio, os, uuid, datetime, httpx
from probes import register_slow


def _payload():
    return {
        "schema_version": "1.0",
        "event_id": str(uuid.uuid4()),
        "event_type": "telemetry",
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "producer": "inspector",
        "severity": "low",
    }


# @register_slow — runs at most once per hour per target.
# Sending 200 requests rapidly; we do NOT use @register because doing this
# every 60 seconds would hammer peer services and potentially take them down.
@register_slow
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    url = f"http://{target_host}/ingest"
    token = os.environ.get("SOC_PROTOCOL_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"}
    hit_429 = False
    last_status = None
    try:
        tasks = [
            http_client.post(url, json=_payload(), headers=headers, timeout=10.0)
            for _ in range(200)
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        statuses = []
        for r in responses:
            if isinstance(r, Exception):
                statuses.append("ERROR")
            else:
                statuses.append(r.status_code)
                if r.status_code == 429:
                    hit_429 = True
        last_status = statuses[-1] if statuses else "ERROR"
        passed = hit_429
        return {
            "check_id":    "C-RATE-001",
            "check_label": "200 rapid requests eventually trigger 429",
            "expected":    429,
            "observed":    429 if hit_429 else last_status,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "high",
            "notes":       "" if passed else "No 429 seen after 200 rapid requests — rate limiting absent or too permissive",
        }
    except Exception as e:
        return {
            "check_id":    "C-RATE-001",
            "check_label": "200 rapid requests eventually trigger 429",
            "expected":    429,
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "high",
            "notes":       str(e),
        }
