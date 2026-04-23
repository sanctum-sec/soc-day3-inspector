# Prompt Library — SOC Compliance Inspector build

**Source:** curated from the STEP UP 3! Kraków workshop (April 2026) — actual prompts the build team used, tagged honest.
**How to read the tags:**

- ⭐ **recommended** — worked reliably, reusable as-is
- ⚠ **careful** — works but requires review / you might accept wrong output
- ❌ **avoid** — too vague, too ambitious, or doesn't respect a contract

The prompts below are grouped by build phase. Use them as starting points; adapt the language to your project's constraints.

---

## Phase 1 — Scaffolding

### ⭐ Initial FastAPI scaffold

```
Start a FastAPI project in ~/app for a SOC compliance inspection tool. Create:
- main.py with /health and /compliance endpoints
- probes/__init__.py — registry pattern for probe modules
- storage/db.py — SQLite schema: findings(finding_id, probe_time, target_tool,
  check_id, check_label, expected, observed, status, severity, notes)
- schemas/envelope.py — shared Pydantic envelope model
- templates/compliance.html — Jinja HTMX dashboard
- scheduler.py — APScheduler, runs every 60 seconds
- systemd unit; requirements.txt.

Don't implement any probes yet — just the skeleton.
```

**What Claude produced:** complete file tree, correct imports, reasonable DB schema, working `/health` endpoint, empty probe registry.
**Accepted:** yes, after read-through.
**Would-change-next-time:** explicitly say "use fastapi>=0.110,<1.0, pydantic>=2,<3" — had to pin versions after the fact.

---

### ⭐ SQLite schema + migration-less bootstrap

```
In storage/db.py, create a function init_schema() that is safe to call on every
startup — use CREATE TABLE IF NOT EXISTS. Schema:

CREATE TABLE findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  probe_time TEXT NOT NULL,        -- ISO-8601 UTC
  target_tool TEXT NOT NULL,
  target_host TEXT NOT NULL,
  check_id TEXT NOT NULL,
  check_label TEXT NOT NULL,
  expected TEXT,
  observed TEXT,
  status TEXT NOT NULL,            -- PASS | FAIL | UNREACHABLE
  severity TEXT NOT NULL,          -- info | low | medium | high | critical
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_findings_probe_time ON findings(probe_time);
CREATE INDEX IF NOT EXISTS idx_findings_target_check ON findings(target_tool, check_id);
```

**What Claude produced:** exactly that, wrapped in a `get_connection()` helper with a contextmanager. Included two convenience methods: `insert_finding(d)` and `recent_findings(limit)`.
**Accepted:** yes.
**Would-change-next-time:** ask for a `prune_old(cutoff_hours=24)` method up-front — we wanted it later.

---

## Phase 2 — Probes (one per file)

### ⭐ Single probe, explicit contract

```
In probes/, create auth_noheader.py. It registers a probe function with the
@register decorator. The function signature is:
    async def check(target_host: str, http_client: httpx.AsyncClient) -> dict

It should POST a minimal valid envelope (no Authorization header) to
http://{target_host}/ingest and return a dict with exactly these keys:
    check_id:    "C-AUTH-001"
    check_label: "POST /ingest with no Authorization returns 401"
    expected:    401
    observed:    r.status_code
    status:      "PASS" if r.status_code == 401 else "FAIL"
    severity:    "high"
    notes:       "" if PASS else "Accepted unauthenticated request"

Exceptions should return status="UNREACHABLE" with the exception text in notes.
```

**What Claude produced:** one file, 35 lines, correct.
**Accepted:** yes.
**Would-change-next-time:** this prompt pattern scaled — we reused it verbatim for 7 more probes with only minor edits.

---

### ⚠ "Add all remaining probes"

```
Now add the other seven probe modules following the same pattern:
- auth_wrongtoken.py (C-AUTH-002)
- schema_nonjson.py (C-SCHEMA-001)
- schema_missingfield.py (C-SCHEMA-002)
- admin_noauth.py (C-ADMIN-001)
- admin_isolation.py (C-ISOLATION-001)
- rate_limit.py (C-RATE-001) — register with @register_slow
- liveness.py (C-LIVE-001)
```

**What Claude produced:** all seven files, mostly correct.
**Accepted:** yes, but with edits.
**Why ⚠:** two issues emerged. (1) The rate-limit probe sent 1000 requests by default (too aggressive — we changed to 200). (2) The admin-isolation probe tested port 8000 vs 8080 — we had to clarify which port the app uses and which is admin. The prompt conflated the two.

**Would-change-next-time:** specify the rate-limit count, the sleep-between-requests, and the exact port numbers per check.

---

## Phase 3 — Dashboard

### ⭐ HTMX dashboard — matrix layout

```
In templates/compliance.html, render a compliance matrix:
- Columns: the 5 SOC tools (trap, scout, analyst, hunter, dispatcher)
- Rows: one per check_id
- Cells: ✓ green for PASS, ✗ red for FAIL, ? gray for UNREACHABLE
- Hover on a cell shows: check time (UTC), expected vs. observed, notes

HTMX: hx-get the partial every 15 seconds to refresh. Public, no auth.
Dark theme. Use system-ui font. Readable at projection distance.
```

**What Claude produced:** one template + a CSS `<style>` block + correct HTMX attributes.
**Accepted:** yes.
**Would-change-next-time:** we added sparkle animations later (unrelated to inspector work); if we wanted those upfront, we'd have asked in the same prompt.

---

### ⚠ Compliance partial for HTMX

```
Create /compliance-partial — renders just the matrix body as HTML, no layout.
The main /compliance page loads this via hx-trigger="load, every 15s".
```

**What Claude produced:** correct endpoint + Jinja template.
**Accepted:** yes.
**Why ⚠:** initially Claude inlined the CSS again in the partial, which broke the dark theme on subsequent refreshes (double-wrapping). We asked it to strip styles from the partial.

---

## Phase 4 — Security layer

### ⭐ Rate-limit the probe engine itself

```
Add a rate limit on our own probe engine: any single target should not be
probed more than once per 60 seconds per check_id. Excess calls should be
dropped (not queued) with a warning in the security log. The existing slow
probes (rate_limit_probe) run on their own 1-hour schedule — don't double
rate-limit them.
```

**What Claude produced:** a decorator `@cooldown(seconds=60)` keyed on `(target, check_id)` and a log entry for drops.
**Accepted:** yes.
**Would-change-next-time:** nothing — this one was perfect first try.

---

### ⭐ Feed-source allowlist (for Scout's feeds)

```
In feeds/, add a hostname allowlist. Fetches should only proceed if the
feed URL's hostname is in the set:
  {urlhaus.abuse.ch, threatfox.abuse.ch, iplists.firehol.org,
   www.spamhaus.org, check.torproject.org}
Anything else: refuse, log to security log, increment a counter.
```

**What Claude produced:** a small `fetch_with_allowlist(url)` helper + 5 lines of tests.
**Accepted:** yes.
**Used by:** Scout. Scales to any tool that pulls from the outside.

---

## Phase 5 — Translate / write

### ⭐ Bilingual translation preserving technical terms

```
Translate this technical document to Ukrainian. Keep technical terms
(FastAPI, Pydantic, bearer token, rate limit, systemd, curl, HTMX) in English.
Match the tone — factual, regulatory, auditor-oriented, not casual.
Don't simplify. Don't add explanations that weren't in the original.
```

**What Claude produced:** a Ukrainian translation that reads naturally, with ~40% English technical words mixed in (exactly what we asked for).
**Accepted:** yes, after a native speaker read-through.
**Would-change-next-time:** for very long docs, ask for translation section-by-section — reduces errors.

---

### ⭐ Explain-line-by-line for code comprehension

```
Explain this Pydantic model line by line, as if I have never used Pydantic.
[paste model]
```

**What Claude produced:** a plain-language walk-through suitable for sharing with a colleague.
**Accepted:** yes.
**Used by:** all teams, heavily. One of the most reusable prompt shapes in the workshop.

---

## Phase 6 — Debugging (patterns to copy)

### ⭐ Minimal diagnostic, with evidence

```
Our /compliance endpoint returns 500. Here is the gunicorn log for the last
30 seconds, the exception traceback, and the exact curl that triggered it.

[paste logs, paste traceback, paste curl]

Propose a minimal fix. Do not refactor. Do not restructure the project.
```

**What Claude produced:** a 3-line diff that fixed the bug.
**Accepted:** yes.
**Why this prompt works:** evidence-first. The AI isn't guessing.

---

### ❌ "Just fix it"

```
The admin page is broken, fix it.
```

**What Claude produced:** a rewrite of three files, most of which was unnecessary.
**Accepted:** no.
**Why this is a ❌:** no evidence, no scope. Claude is now trying to be helpful by doing a lot, when you wanted a small change. Always paste logs.

---

## Phase 7 — Document / report

### ⭐ Draft inspection checklist from running probes

```
Take the list of eight probe modules under probes/ (paste them). Draft a
regulator-facing inspection checklist. For each probe, produce:
- Check ID
- What it tests (one sentence, plain language)
- Manual verification command (curl one-liner)
- Expected result
- What failure implies (1-2 sentences)

Format as Markdown table or section headings. Keep it factual, regulator-
oriented. Do not add generic security advice. Output in English first, then
translate to Ukrainian preserving technical terms.
```

**What Claude produced:** a 100% usable first draft of what became `inspection-checklist.{en,uk}.md`.
**Accepted:** yes, after a pass to fix port numbers and one verification command that used the wrong HTTP verb.
**Would-change-next-time:** paste the actual probe module source so the AI can copy the exact check_id and check_label strings instead of making them up.

---

### ⭐ Lessons-learned draft from methodology journal

```
Read methodology-journal.md (attached). Produce a 1–2 page lessons-learned
document in Ukrainian. Structure: "what worked", "what didn't work", "what
we'd do differently". Evidence-based — cite specific journal entries. Do not
fabricate lessons that aren't supported by the journal.
```

**What Claude produced:** a good draft if the journal had real entries. (Ours was sparse, so the output was sparse too. Honesty flows from data.)
**Accepted:** partially — we filled in the gaps manually.

---

## Patterns across all phases

Looking at the above, a few meta-patterns show up:

1. **Prompts that include an explicit contract (types, return shape, failure semantics) produce reusable, reviewable code.** That's 80% of the ⭐s.

2. **Prompts that include evidence (logs, payloads, exact commands) debug fast.** Evidence-less debug prompts produce rewrites.

3. **Prompts that describe the audience (regulator, Ukrainian-speaking, projection-distance) produce appropriately-toned output.** The AI will match formality if you ask.

4. **Prompts that say "do not …" prevent scope creep.** "Do not refactor," "do not add features I didn't ask for," "do not add required fields."

5. **The "explain line by line" prompt is disproportionately valuable.** Use it every time you inherit code.

---

## Starter set for your HQ

If you only take five prompts back, take these:

1. The **scaffold prompt** from Phase 1 (adapt the files list).
2. The **single-probe with explicit contract** from Phase 2.
3. The **minimal diagnostic with evidence** from Phase 6.
4. The **bilingual translation preserving technical terms** from Phase 5.
5. The **explain-line-by-line** from Phase 5.

These five cover ~80% of the work we did in the workshop.
