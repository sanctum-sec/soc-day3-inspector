> **Українська версія:** [README.md](README.md)

# Team 6 — Inspector (Інспектор): Compliance, Audit & Training Builder

**Your Lightsail:** `wic06.sanctumsec.com` (18.185.169.40)
**Your GitHub repo:** `https://github.com/sanctum-sec/soc-day3-inspector`
**Read first:** [`sanctum-sec/soc-protocol`](https://github.com/sanctum-sec/soc-protocol) — this is the contract every other team is supposed to follow, and the source of truth you inspect them against.

---

## 1. Your mission — two deliverables, not one

You are the SOC's **regulator**. Where the other five teams *build* the SOC, you *inspect* it against the declared protocol and policies — then you **turn what you learned into training material you can hand to your counterparts at HQ.**

By end of day you will have produced **two things**, both of which matter equally:

### 1a. A live compliance-inspection tool
- A probe that continuously checks each of the 5 SOC tools against the shared contract
- A read-only compliance dashboard anyone can look at
- A findings log (what passed, what failed, when, why)

### 1b. A take-home training package for your HQ
- Bilingual **inspection checklist** (EN + UK) — reusable at SNRIU or any SOC you oversee back home
- A **"How to inspect a SOC" runbook** (UA-first) — teachable walkthrough for your counterparts
- An **"AI-assisted build methodology"** document (UA + EN) — *how* you used Claude Code today to build the inspection tool in one day, with the actual prompts, decisions, and lessons learned. This is the part that will multiply your impact at HQ: it turns one day of workshop time into a reusable training module.
- A **reusable prompt library** — annotated, labelled by what worked and what didn't.

The training package is not decoration. It **is** the deliverable. The inspection tool is what gives you credibility to teach.

---

## 2. Where this fits in a real SOC

From Table 1 of MITRE's *11 Strategies of a World-Class SOC* (2022):

- **External Training and Education** — your primary function today.
- **Situational Awareness and Communications** — compliance dashboard is the regulator's view.
- **Vulnerability Assessment** — you are literally testing for control weaknesses in peer tools.
- **Metrics** — you define what "compliant" means and measure it.
- **Strategy, Planning, and Process Improvement** — your findings drive other teams to improve.

In regulated industries (nuclear, finance, healthcare) this role has a name: the internal audit function. In less regulated shops it's "GRC" (Governance, Risk, Compliance). In both cases, it's the function that makes the other five honest.

---

## 3. Access and what's already on your Lightsail

```
ssh ubuntu@wic06.sanctumsec.com
# password: GhostTrace-06!
```

Pre-installed: git, Python 3.10 + pip, Node.js LTS, `claude`, `codex`, AWS CLI + credentials for `s3://wic-krakow-2026`, jupyter + pandas/numpy/matplotlib/seaborn/scikit-learn/requests/httpx, plus `SOC_PROTOCOL_TOKEN` in `~/.soc_env`.

Ports open: 22 (SSH), 80 (HTTP), 8000 (your app), 8001 (your admin page).

---

## 4. Data flows

Unlike Teams 1–5, you are a **pure consumer** of the other tools — a read-only observer. You do not emit events into the shared protocol. Your outputs are **reports, dashboards, and training artifacts**, not events.

### 4.1 What you consume (inputs)

From each of the 5 SOC tools on their public IPs:

| Probe type                 | Endpoint tested                                            | Expected outcome                                  |
| -------------------------- | ---------------------------------------------------------- | ------------------------------------------------- |
| Liveness                   | `GET /health`                                              | 200, `{"status":"ok","tool":"<name>"}`            |
| Unauthenticated write      | `POST /ingest` (no `Authorization` header)                 | 401                                               |
| Bad token                  | `POST /ingest` with a deliberately-wrong bearer            | 401                                               |
| Malformed JSON             | `POST /ingest` with bad body (e.g., not JSON)              | 400                                               |
| Schema violation           | `POST /ingest` with missing required envelope fields       | 400                                               |
| Wrong event_type           | Sending an `event_type` the target isn't supposed to accept | 400                                               |
| Rate-limit enforcement     | Burst 200 valid requests in 60 s                           | Should hit 429 before the end                     |
| Admin isolation            | `GET <host>:8001/admin` without auth                        | 401                                               |
| Admin auth works           | `GET <host>:8001/admin` with Basic Auth                     | 200                                               |

### 4.2 What you produce (outputs)

| Output                                   | Location                                                                 | Audience                                |
| ---------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------- |
| Live compliance dashboard                | `http://wic06.sanctumsec.com:8000/compliance`                            | Anyone on the workshop LAN              |
| Findings JSON API                        | `GET http://wic06.sanctumsec.com:8000/findings`                          | Dispatcher's dashboard + anyone curious |
| Admin page                               | `http://wic06.sanctumsec.com:8001/admin` (Basic Auth)                    | Your team only                          |
| Health endpoint (yours)                  | `GET http://wic06.sanctumsec.com:8000/health`                            | Everyone                                |
| **Training artifacts (S3)**              | `s3://wic-krakow-2026/public/inspector/*`                                | Your HQ counterparts, visible on the workshop landing page once uploaded |

### 4.3 Example finding record

Your findings table stores one row per probe-execution:

```json
{
  "finding_id": "F-2026-0001",
  "probe_time": "2026-04-23T11:02:14Z",
  "target_tool": "scout",
  "target_host": "wic02.sanctumsec.com:8000",
  "check_id": "C-AUTH-001",
  "check_label": "POST /ingest without Authorization returns 401",
  "expected": 401,
  "observed": 200,
  "status": "FAIL",
  "severity": "high",
  "notes": "Endpoint accepted unauthenticated request — violates soc-protocol §7.1"
}
```

---

## 5. Architecture — four layers (not three)

You build everything the other teams build, plus one unique layer.

### 5.1 The probe engine

A small Python module that runs every ~60 seconds and executes every registered check against every registered target. Results get appended to `findings.db` (SQLite). Each check is one Python function returning `{status, expected, observed, notes}`.

Suggested **minimum 8 checks** (can add more later):

| Check ID       | What it tests                                                          |
| -------------- | ---------------------------------------------------------------------- |
| `C-LIVE-001`   | `GET /health` returns 200                                              |
| `C-AUTH-001`   | `POST /ingest` with no bearer returns 401                              |
| `C-AUTH-002`   | `POST /ingest` with wrong bearer returns 401                           |
| `C-SCHEMA-001` | Non-JSON body returns 400                                              |
| `C-SCHEMA-002` | Envelope with no `event_type` returns 400                              |
| `C-RATE-001`   | 200 rapid valid requests eventually trigger 429                        |
| `C-ADMIN-001`  | `GET <host>:8001/admin` without auth returns 401                       |
| `C-ISOLATION-001` | App port (8000) does not expose admin routes                        |

### 5.2 The compliance dashboard

A FastAPI page at `/compliance` showing a live matrix: rows are the 5 tools, columns are the checks, cells are ✓ / ✗ / ? with hover-detail. Auto-refreshes every 15 s. Public (read-only, no auth) — this is the regulator-facing view.

### 5.3 The admin page (port 8001)

Same requirements as every other team — two tabs (Operational + Security). Basic Auth behind `ADMIN_USER` / `ADMIN_PASS`. Shows:

- Operational: checks run/hour, failures today, per-target status, probe queue depth
- Security: auth failures against your own `/findings` if you guard it, rate-limit trips, probe-engine crashes

### 5.4 The training-artifact builder *(your unique layer)*

A set of Markdown files your team authors during the day and publishes to `s3://wic-krakow-2026/public/inspector/` at the end. These are the take-home:

| File                                     | Description                                                                                                                  |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `inspection-checklist.en.md`             | Table of every check, what it tests, how to run it manually, what pass/fail look like. **Reusable at HQ against any SOC.**    |
| `inspection-checklist.uk.md`             | Same, in Ukrainian.                                                                                                           |
| `how-to-inspect-a-soc.uk.md`             | A narrative runbook: "Given you are inspecting a SOC, here's a proposed order of operations and what to do with findings."    |
| `ai-assisted-build-methodology.uk.md`    | **The core training deliverable.** Describes HOW you used Claude Code to build everything today: the prompts that worked, the ones that didn't, decision points, verification techniques, how to critically read AI-generated code. This becomes an AI-methodology training module at your HQ. |
| `ai-assisted-build-methodology.en.md`    | English version for bilingual sharing.                                                                                        |
| `prompt-library.md`                      | Curated, annotated list of the prompts your team actually used. Each with a short note: what it produced, whether you accepted it, and what you'd change. |
| `lessons-learned.uk.md`                  | "What surprised us. What we'd do differently. What we still don't understand." — the honest retrospective.                   |

**Structure of the methodology doc** (the most important artifact): write it as if you're teaching a colleague who has never used Claude Code. Include screenshots of actual prompt → output exchanges (sanitized). This is what multiplies the workshop's impact — one day of your time becomes ongoing training capacity.

---

## 6. Recommended stack (not mandatory)

| Concern           | Recommendation                           | Why                                                                 |
| ----------------- | ---------------------------------------- | ------------------------------------------------------------------- |
| Language          | **Python 3.10**                          | Pre-installed with the full data-science toolkit                    |
| HTTP              | **FastAPI** + Uvicorn                    | Matches peer teams — your probes hit their FastAPI endpoints        |
| HTTP client       | **httpx** (async)                        | Probing 5 targets × 8 checks = 40 calls per cycle — async helps     |
| Store             | **SQLite** (`findings.db`)               | Plenty for one day                                                  |
| Dashboard UI      | FastAPI + Jinja + HTMX                   | Consistent with peers                                               |
| Scheduler         | APScheduler, or a simple asyncio loop    | Probe every 60 s                                                    |
| Artifact authoring | Just **Markdown in your repo**           | `git push` is your "publish". S3 upload is the final distribution   |

---

## 7. Security infrastructure — non-negotiable (and meta)

You are building a tool that probes *for* security weaknesses. Its own security matters twice as much.

- [ ] Bearer token on any write endpoint you expose (`/findings` can stay public read-only, but not writable)
- [ ] HTTP Basic on the admin page
- [ ] Rate-limit **your own probes** — max 1 probe-cycle per target per minute. Probing faster risks taking a peer down, which would be a terrible look for the audit team.
- [ ] Log every probe you send (probe log) AND every probe response (response log) AND every probe-engine crash (security log). Your transparency is your credibility.
- [ ] **Do not** try to brute-force or exploit — you're testing declared-contract compliance, not doing red-team work. If you find a real vulnerability, stop, write it up, and report it to the facilitator.
- [ ] Clear scope declaration: publish *what you probe for* on `/compliance`. No hidden checks.

Ask Claude: *"Add rate limiting on my probe engine: each target is probed at most once every 60 seconds per check. If I try to probe more frequently, queue and delay."*

---

## 8. Admin page spec

URL: `http://wic06.sanctumsec.com:8001/admin`, HTTP Basic.

**Operational:**
- Checks executed in last 5 min / 1 h / 24 h
- Per-target compliance percentage (pass/total)
- Per-check failure rate across all targets
- Probe queue depth
- Delivery health: can you reach each target's `/health`?

**Security:**
- Auth failures against your own endpoints
- Rate-limit trips (on probe submission)
- Probe-engine exceptions
- Responses from peers that looked like they might have been a peer-side bug vs. a genuine non-conformity — you want to catch the case where a peer's service crashed rather than politely refused

---

## 9. Your day — phase by phase with Claude

### Phase 0 — Kickoff (9:15–10:00)

Attend the facilitator-led protocol session. **Pay close attention to what the 5 contract clauses actually say** — those become your checks. Decide roles.

**Unique to your team:** start a `methodology-journal.md` in your repo *now* and begin logging every prompt you give Claude plus a one-line note on the result. This is the raw material for your ai-assisted-build-methodology doc.

### Phase 1 — Scaffold (10:00–10:45)

```
Start a FastAPI project in ~/app for a SOC compliance inspection tool. Create:
- main.py with /health, /findings (GET, returns recent findings),
  /compliance (GET, renders the matrix dashboard).
- probes/__init__.py — registry pattern for probe modules.
- storage/db.py — SQLite schema: findings (finding_id, probe_time, target_tool,
  target_host, check_id, check_label, expected, observed, status, severity, notes).
- schemas/envelope.py — shared Pydantic envelope for when WE POST to peers.
- templates/compliance.html — Jinja matrix template.
- scheduler.py — background task that runs every 60 seconds.
- systemd unit. requirements.txt: fastapi uvicorn httpx apscheduler pydantic jinja2.

Commit the scaffold. Keep methodology-journal.md updated with the prompt I used above
and a one-line note: what did Claude generate, what did we accept, what did we change?
```

### Phase 2 — First probes (10:45–12:00)

Start with the easiest check — liveness — hit all 5 tools. You'll discover which of them are actually up (some may still be in mock phase at this hour — that's a valid finding in itself).

```
Create ~/app/probes/liveness.py with an async function check(target_host, http_client)
that GETs http://{target_host}/health with a 3-second timeout. Returns a dict with
{check_id: "C-LIVE-001", expected: 200, observed: <status>, status: "PASS"|"FAIL"|"UNREACHABLE", notes}.

Create ~/app/targets.py as a list of 5 dicts: trap (wic01), scout (wic02), analyst (wic03),
hunter (wic04), dispatcher (wic05). Each has tool name + host.

Wire scheduler.py to run ALL registered probes against ALL targets every 60 seconds,
write findings to the database. Run it.

Verify findings.db fills up. Serve /findings.
```

**Checkpoint at 12:00.** Lunch. Before leaving: commit, deploy, verify at least one check runs successfully.

### Phase 3 — Compliance checks (13:00–14:30)

Add the auth and schema checks. This is where your work starts *finding things*.

```
Add seven more probe modules under ~/app/probes/:
- auth_noheader.py — C-AUTH-001 — POST /ingest with no Authorization header, expect 401.
- auth_wrongtoken.py — C-AUTH-002 — POST /ingest with "Authorization: Bearer NOT_THE_TOKEN", expect 401.
- schema_nonjson.py — C-SCHEMA-001 — POST /ingest with body="<html>", expect 400.
- schema_missingfield.py — C-SCHEMA-002 — POST /ingest with {"event_type": "telemetry"} only, expect 400.
- rate_limit.py — C-RATE-001 — send 200 legitimate POSTs in 60 seconds using a valid bearer; expect at least one 429.
  THIS ONE IS DANGEROUS. Run it once per hour per target, not every minute. Put it on a separate slow schedule.
- admin_noauth.py — C-ADMIN-001 — GET http://target:8001/admin, expect 401.
- admin_isolation.py — C-ISOLATION-001 — GET http://target:8000/admin, expect 404 (admin must not be on app port).
```

### Phase 4 — Compliance dashboard (14:30–15:30)

```
Fill in templates/compliance.html. Render a table:
- Columns: 5 tools (trap, scout, analyst, hunter, dispatcher)
- Rows: one per check_id
- Cells: ✓ (green, all recent results PASS), ✗ (red, any FAIL in last 10 min),
  ? (gray, no recent data or UNREACHABLE)
- Hover on a cell shows the most recent finding: expected vs observed, notes, time.

Below the table, show the 20 most-recent findings.

HTMX hx-get with every-15s refresh on the matrix.
Public (no auth). Dark-ish theme, readable at projection distance.
```

### Phase 5 — Admin page + hardening (15:30–16:30)

```
Create ~/app/admin/ on port 8001, HTTP Basic (ADMIN_USER, ADMIN_PASS from env).
- Operational tab: checks executed in last 5m / 1h / 24h, per-target compliance %,
  per-check failure rate, probe queue depth.
- Security tab: auth failures on any write endpoint, rate-limit trips on probe
  submission, probe-engine exceptions (from try/except), responses from peers
  that looked like crashes vs policy violations.

Also add a probe-rate limiter: reject internal calls to run_probe(...) that try
to probe the same (target, check) combination more than once per 60 seconds.
```

### Phase 6 — Training artifacts (16:30–17:15) — *the regulator-unique phase*

This phase is at least as important as the technical work above.

Each team member owns one artifact. Use Claude as your writing assistant:

- **Inspection-checklist (bilingual):**
  ```
  Take my list of 8 compliance checks from probes/ and draft an inspection
  checklist formatted for a regulatory inspector. Columns: check ID, what's
  being tested, why it matters, how to verify manually (curl command),
  expected result, failure implications. Output in English first, then translate
  to Ukrainian, preserving technical terms in English.
  ```

- **How-to-inspect runbook (UA-primary):**
  ```
  Write a Ukrainian-language runbook for a regulatory inspector arriving at
  a SOC for the first time. Cover: what to ask the SOC manager, how to read
  their declared contract, how to design your own check list, how to sample
  without overwhelming operators, how to write findings, how to distinguish
  non-conformity from implementation variance. Aim for 2–3 pages.
  ```

- **AI-methodology doc (UA+EN):**
  ```
  Read my methodology-journal.md (the log of every prompt we used today and
  what Claude produced). Reorganize it into a training document titled
  "How we used AI to build a SOC compliance inspector in one day." Include:
  (1) an honest preamble — what AI is and isn't good at in this context;
  (2) the prompt patterns that worked (with examples);
  (3) verification techniques — how we avoided accepting broken code;
  (4) moments where the AI was wrong and how we caught it;
  (5) a reusable prompt library;
  (6) limitations and when to stop using AI and think yourself.
  Write the primary version in Ukrainian, then an English translation.
  ```

- **Prompt library:** curate from `methodology-journal.md` — one Markdown file, each prompt with its result summary and a `⭐ recommended` / `⚠ careful` / `❌ avoid` tag.

- **Lessons-learned:** 1–2 page honest retrospective, Ukrainian.

Upload all artifacts to `s3://wic-krakow-2026/public/inspector/` so they appear on the workshop landing page.

### Phase 7 — Demo prep (17:15–17:30)

- Load the compliance dashboard on a big screen
- Pick one failing check to narrate: "Here's what our probe did, here's what Scout returned, here's why it's a non-conformity, here's what we would tell Scout to fix"
- Volunteer someone to present the take-home training package

---

## 10. Splitting the work across 3–5 people

If you have **3**:

| Role                    | Owns                                                   |
| ----------------------- | ------------------------------------------------------ |
| Probe engineer          | All 8 probes + scheduler + findings store              |
| Dashboard + admin       | /compliance dashboard, admin page, deploy              |
| Training artifacts lead | Methodology journal, 6 take-home documents             |

If you have **4**:

| Role                     | Owns                                            |
| ------------------------ | ----------------------------------------------- |
| Probe engineer           | All 8 probes + scheduler                        |
| Platform + storage       | FastAPI, findings DB, findings API              |
| Dashboard + admin        | /compliance, admin, deploy                      |
| Training artifacts lead  | Methodology journal + all 6 documents           |

If you have **5**:

Split "training artifacts" into (a) inspection-checklist + runbook (workshop domain) and (b) AI-methodology + prompt library + lessons-learned (teaching-about-AI domain). Both roles keep the methodology journal updated together.

---

## 11. Mock-first checklist

By 11:00:

- [ ] `GET /health` works
- [ ] `GET /findings` returns at least 3 hand-rolled fake findings (so Dispatcher can see the shape)
- [ ] `GET /compliance` returns a static HTML matrix (no real data yet)
- [ ] `methodology-journal.md` has at least 3 entries from the morning's prompts

---

## 12. Definition of done

**Minimum viable — the tool:**
- [ ] Probes running against all 5 tools on a 60-second loop
- [ ] At least 6 of 8 checks implemented
- [ ] Findings stored in SQLite
- [ ] `/compliance` live, showing current matrix
- [ ] Admin page on 8001 with both tabs
- [ ] Bearer auth on write endpoints, rate limiting, schema validation
- [ ] systemd + GitHub Actions deploy

**Minimum viable — the training package:**
- [ ] Inspection checklist (EN + UK)
- [ ] How-to-inspect runbook (UA)
- [ ] AI-methodology doc (UA primary, EN translation)
- [ ] Prompt library
- [ ] Lessons learned
- [ ] All 6 files uploaded to `s3://wic-krakow-2026/public/inspector/`

**Bonus:**
- [ ] All 8 checks
- [ ] A read-only public `/inspection-report` HTML page that concatenates all your findings into an auditor-style report
- [ ] Auto-publish your findings to the shared landing page at `https://wic-krakow.sanctumsec.com/`

---

## 13. Stretch goals (if you're ahead)

- Add a per-tool "compliance score" (weighted average of checks) and track it over time
- Email/Telegram digest at the end of the day summarizing each tool's compliance posture
- Extend the training package to include a sample 5-page "inspection report" you could hand to a plant manager after a real audit
- A short screencast walking through your tool, narrated in Ukrainian, archived with the training materials

Good hunting — and enjoy being the team that gets to be right.
