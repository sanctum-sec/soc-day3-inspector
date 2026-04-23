# SOC Compliance Inspection Checklist

**Source:** Team 6 — Inspector, STEP UP 3! Kraków 2026
**Purpose:** a reusable checklist a regulatory inspector can bring to any Security Operations Center to verify protocol compliance. Eight checks, each with a manual verification command, expected result, and the security property it confirms.

Use it exactly as written for a first-pass audit. Any `FAIL` is a non-conformity the SOC operator must remediate before close-out.

---

## How to use this checklist

1. Establish scope with the SOC operator — which tools / hosts / ports are in-scope? Get the operator to declare which endpoints are supposed to be public vs. protected.
2. For each check below, run the listed command from a workstation that is **outside** the SOC's trust boundary. Do not run checks from inside the SOC's network — you need to verify what an external adversary sees.
3. Record `expected` vs. `observed` for every run. Any deviation is a finding — do **not** judge severity in the field. Write everything down; triage later.
4. After completing all checks, walk the operator through the findings. The order of the checks below is deliberate: the later checks assume earlier ones passed.

For audit transparency, your checks and your probing cadence should be declared up-front to the SOC operator. Sustained flooding of a target is not acceptable.

---

## The eight checks

### C-LIVE-001 — Service liveness

**What it tests:** that the tool is running and reachable.

**Manual verification:**
```
curl -i --max-time 3 http://<host>:<port>/health
```

**Expected:** HTTP 200, body is JSON containing at minimum `"status": "ok"`.

**Failure implications:** if a tool is down, no other check is meaningful. Mark this `UNREACHABLE` and move on; re-run all checks after the tool comes back.

---

### C-AUTH-001 — Unauthenticated write is rejected

**What it tests:** the SOC's `/ingest` endpoint rejects requests that have no `Authorization` header at all.

**Manual verification:**
```
curl -i -X POST --max-time 5 \
  http://<host>:<port>/ingest \
  -H "Content-Type: application/json" \
  -d '{"schema_version":"1.0","event_id":"test-0001","event_type":"telemetry","timestamp":"2026-04-23T10:00:00Z","producer":"inspector","severity":"low"}'
```

**Expected:** HTTP **401**.

**Failure implications:** if a `200`/`202` is returned, any internet user can inject arbitrary events into the SOC pipeline. This is a direct violation of the declared protocol §7.1 (bearer-token required on `/ingest`).

---

### C-AUTH-002 — Wrong bearer token is rejected

**What it tests:** the endpoint validates the token value, not just its presence.

**Manual verification:**
```
curl -i -X POST --max-time 5 \
  http://<host>:<port>/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer WRONG_TOKEN_XYZ" \
  -d '{"schema_version":"1.0","event_id":"test-0002","event_type":"telemetry","timestamp":"2026-04-23T10:00:00Z","producer":"inspector","severity":"low"}'
```

**Expected:** HTTP **401**.

**Failure implications:** if a wrong token is accepted, the bearer check is cosmetic. Attackers frequently probe by sending `Bearer anything` — unreported acceptance here is equivalent to no auth.

---

### C-SCHEMA-001 — Non-JSON body is rejected

**What it tests:** input validation on `/ingest`. The endpoint must not crash, 500, or accept non-JSON.

**Manual verification:**
```
curl -i -X POST --max-time 5 \
  http://<host>:<port>/ingest \
  -H "Authorization: Bearer <valid-token>" \
  -H "Content-Type: text/plain" \
  -d 'this is not json at all'
```

**Expected:** HTTP **400**.

**Failure implications:** `500` here indicates an unhandled exception path — a reliability problem and a denial-of-service vector. `200`/`202` indicates the endpoint silently discards malformed input without recording a security event.

---

### C-SCHEMA-002 — Missing required envelope fields are rejected

**What it tests:** the endpoint rejects events that are missing mandatory envelope fields (`schema_version`, `event_id`, `event_type`, `timestamp`, `producer`, `severity`).

**Manual verification:**
```
curl -i -X POST --max-time 5 \
  http://<host>:<port>/ingest \
  -H "Authorization: Bearer <valid-token>" \
  -H "Content-Type: application/json" \
  -d '{"event_type":"telemetry"}'
```

**Expected:** HTTP **400**.

**Failure implications:** if under-specified events are accepted, downstream correlation in the SIEM and the SOAR cannot rely on any field being present. The contract with downstream tools breaks silently.

---

### C-RATE-001 — Rate limit eventually triggers

**What it tests:** sustained high-rate POSTs to `/ingest` (with a valid token and valid payload) eventually hit an explicit rate limit.

**Manual verification:**
```
for i in $(seq 1 200); do
  curl -sS -o /dev/null -w "%{http_code}\n" -X POST \
    http://<host>:<port>/ingest \
    -H "Authorization: Bearer <valid-token>" \
    -H "Content-Type: application/json" \
    -d "{\"schema_version\":\"1.0\",\"event_id\":\"burst-$i\",\"event_type\":\"telemetry\",\"timestamp\":\"2026-04-23T10:00:00Z\",\"producer\":\"inspector\",\"severity\":\"low\"}"
done | sort | uniq -c
```

**Expected:** at least one HTTP **429** in the response code distribution.

**Failure implications:** if every request returns 202 under flood, the tool has no rate limit and a legitimate peer (or a compromised one) can saturate the pipeline.

**Auditor note:** run this check at most **once per hour** per target. Repeated fast firing stops being a probe and starts being a denial-of-service test; stay on the right side of that line.

---

### C-ADMIN-001 — Admin page rejects unauthenticated access

**What it tests:** the admin page on port 8001 requires authentication.

**Manual verification:**
```
curl -i --max-time 3 http://<host>:8001/admin
```

**Expected:** HTTP **401**.

**Failure implications:** operator configuration or audit surfaces that leak without auth are a classical SOC mis-configuration. Attackers enumerate `/admin`, `/dashboard`, `/console` constantly.

---

### C-ISOLATION-001 — Admin routes are not served on the app port

**What it tests:** admin routes live **only** on port 8001. The public app port (8000) must not serve any admin route.

**Manual verification:**
```
curl -i --max-time 3 http://<host>:8000/admin
```

**Expected:** HTTP **404**.

**Failure implications:** a `401` or `200` here indicates the admin app is bound to the public port. Even if it's credential-protected, any CVE in the admin stack becomes internet-exposed. The protocol's port-segregation convention exists precisely to shrink that blast radius.

---

## Reporting a finding

For any `FAIL`, record:

| Field | Example |
| ----- | ------- |
| Check ID | `C-AUTH-001` |
| Target (host + port) | `wic03.sanctumsec.com:8000` |
| Time of observation (UTC) | `2026-04-23T14:02:14Z` |
| Expected | `401` |
| Observed | `202` |
| Reproduction command | (paste the exact `curl` invocation) |
| Evidence | (response headers + first 500 bytes of body) |
| Recommended remediation | short, actionable — don't write architecture advice here |

Keep findings factual. Remediation advice goes in a separate section or a follow-up engagement.

---

## What this checklist does *not* cover

- Anti-abuse controls beyond rate limits (e.g., IP reputation, geo-blocking, captchas)
- Secret hygiene (audit of code for hardcoded tokens/passwords — do that separately against the source repo)
- Operational telemetry (logs, metrics, audit trails)
- Incident-response runbooks
- Availability / DR posture

Those are deeper engagements. This checklist is a **30-minute external-perimeter compliance check** you can run against any SOC that has declared they implement the `soc-protocol` contract.
