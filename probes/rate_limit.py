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
# Sending 200 requests rapidly; NOT @register because doing this every 60 seconds
# would hammer peer services and risk taking them down.
@register_slow
async def check(target_host: str, http_client: httpx.AsyncClient) -> dict:
    url = f"http://{target_host}/ingest"
    token = os.environ.get("SOC_PROTOCOL_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"}

    # Use a dedicated client with a higher connection pool for the burst
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    try:
        async with httpx.AsyncClient(limits=limits, timeout=10.0) as burst_client:
            tasks = [
                burst_client.post(url, json=_payload(), headers=headers)
                for _ in range(200)
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        count_429 = 0
        count_ok  = 0
        count_err = 0
        for r in responses:
            if isinstance(r, Exception):
                count_err += 1
            elif r.status_code == 429:
                count_429 += 1
            else:
                count_ok += 1

        # If we couldn't reach the service at all, mark unreachable
        if count_ok == 0 and count_429 == 0:
            return {
                "check_id":    "C-RATE-001",
                "check_label": "200 rapid requests eventually trigger 429",
                "expected":    429,
                "observed":    f"0/200 reachable",
                "status":      "UNREACHABLE",
                "severity":    "high",
                "notes":       f"All {count_err} requests failed — service may be down or /ingest not deployed",
            }

        passed = count_429 > 0
        summary = f"{count_429}×429 / {count_ok}×other / {count_err}×err in 200 req"
        return {
            "check_id":    "C-RATE-001",
            "check_label": "200 rapid requests eventually trigger 429",
            "expected":    "≥1×429",
            "observed":    summary,
            "status":      "PASS" if passed else "FAIL",
            "severity":    "high",
            "notes":       "" if passed else "No 429 returned — rate limiting absent or threshold > 200 req/min",
        }
    except Exception as e:
        return {
            "check_id":    "C-RATE-001",
            "check_label": "200 rapid requests eventually trigger 429",
            "expected":    "≥1×429",
            "observed":    "ERROR",
            "status":      "UNREACHABLE",
            "severity":    "high",
            "notes":       str(e),
        }
