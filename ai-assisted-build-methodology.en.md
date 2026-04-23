# How we used AI to build a SOC compliance inspector in one day

**Audience:** regulators, auditors, and technical supervisors who will be asked "can you bring this back to HQ and teach it?"
**Premise:** a team of six regulators, many of whom had not used Claude Code before that morning, built a working compliance-inspection tool AND a bilingual take-home training pack in about seven hours, during the STEP UP 3! workshop in Kraków (April 2026).
**What this document is:** an honest account of *how* that was done — which prompts worked, which didn't, where the AI was wrong, and what verification techniques let us ship a tool we actually trust.

---

## 1. An honest preamble — what AI is and isn't good at here

AI (specifically Claude Code, the terminal-based agent version of Claude) is **extraordinarily good at**:

- Turning a one-sentence specification of a component into a working first draft.
- Translating one language into another (Python → Bash, English → Ukrainian, YAML → Python).
- Explaining unfamiliar code we pulled from GitHub or a peer team.
- Catching boilerplate mistakes (forgotten imports, wrong type annotations).
- Maintaining consistency across a dozen files (renaming, refactoring, applying the same pattern everywhere).
- Writing plausible-looking test fixtures.

It is **not yet reliably good at**:

- Making architectural decisions. When asked "should we use X or Y?", it tends to give you a balanced summary, not a recommendation grounded in your specific constraints.
- Noticing that something that compiles is *semantically* wrong. A bearer-token check that always passes will compile just fine.
- Staying within declared scope. A prompt like "build me a compliance dashboard" will often come back with HTMX auto-refresh you didn't ask for. That's usually a bonus, but it's also scope creep.
- Telling you when it doesn't know. It will confidently synthesize an answer that looks right. You still have to verify.

These limits are not theoretical for us — we hit every one of them during the workshop. They're the reason the next sections are *mostly about verification*, not about getting better at prompting.

---

## 2. The prompt patterns that worked

These are patterns, not exact texts — adapt to your task.

### 2.1 Scaffold-first, refine-later

Bad prompt: *"Build me a complete SOC compliance inspector."*
(Comes back with 400 lines of code mixing concerns, hard to verify.)

Better prompt:

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

You get back a clean skeleton. Review it. Deploy. Then add one probe.

**Why this works:** breaks the problem into reviewable pieces. Each Claude response is small enough that you can read the whole thing. Compounding confidence.

### 2.2 One feature at a time, with explicit contract

```
In probes/, create auth_noheader.py. It registers a probe function with the
@register decorator. The function signature is:
    async def check(target_host: str, http_client: httpx.AsyncClient) -> dict

It should POST a minimal but valid envelope (no Authorization header) to
http://{target_host}/ingest and return a dict with:
    {check_id: "C-AUTH-001", expected: 401, observed: r.status_code,
     status: "PASS"|"FAIL"|"UNREACHABLE", severity: "high", notes: ...}

Exceptions should return status=UNREACHABLE with the exception text in notes.
```

Specify **types, return shape, error behavior**. The AI fills in the body. You review.

**Why this works:** the AI can't drift from your contract if the contract is in the prompt. You're delegating implementation, not design.

### 2.3 "Make it testable"

```
Write three pytest tests for this auth_noheader probe using respx to mock the
target. Test: (1) 401 → PASS, (2) 200 → FAIL, (3) connection error → UNREACHABLE.
```

AI writes tests faster than humans do. The tests also double as documentation of the intended behavior — future you, reading them, understands the function's contract in 30 seconds.

### 2.4 Explain-this

```
Explain what this Pydantic model does line by line, as if I have never used Pydantic.
[paste model]
```

This is a 10-second prompt that can save a team member 30 minutes of documentation-reading. Do it whenever you inherit code from Claude or from a peer team.

### 2.5 Bilingual translate-preserving-terms

```
Translate this technical document to Ukrainian. Keep technical terms
(FastAPI, Pydantic, bearer token, rate limit, systemd, curl) in English.
Match the tone — factual, regulatory, auditor-oriented. Don't make it more casual.
```

The AI preserves English technical vocabulary by default when asked. Without this instruction, it will sometimes over-translate and give you "обмежувач швидкості" instead of "rate limit."

### 2.6 Prompt the critic

After Claude writes something, **don't just accept it**. Run a second prompt:

```
Read the code I just asked you to write. What could go wrong in production?
What are the 3 edge cases you didn't handle?
```

Often the AI will identify the holes itself. This is much cheaper than finding them in the field.

---

## 3. Prompts that did not work well

### 3.1 "Deploy the whole thing to production"

If you ask Claude to `systemctl restart` your service or to deploy via a remote SSH, it will often do it — but if it fails, you have no idea what state the server is in. Keep deployments manual and explicit. Claude writes the deploy script, *you* run it.

### 3.2 "Figure out why it's not working"

```
The /compliance endpoint is returning 500. Fix it.
```

This is a cry for help that leaves Claude guessing. Better:

```
Here are the last 30 lines of the gunicorn log. Here's the exception. Here's the
request that triggered it. Propose a minimal fix (not a rewrite).
```

The more evidence you paste, the more useful the response.

### 3.3 "Make it fast"

Claude will add caching, async, threads, and premature optimization if you let it. Don't ask for "fast." Ask for "meets a 15-second refresh target" with a measurable bar.

### 3.4 "Match the existing code style"

The AI has no memory across prompts unless you re-paste. Asking it to "match the style of the rest of the project" without attaching an example will produce something confident but wrong. Paste a representative file and say "match this structure."

---

## 4. Verification techniques — how we avoided shipping broken code

We did not blindly trust the AI. Every piece that went to production was verified. Some of the techniques we used:

### 4.1 The three-second eyeball test

For every file the AI generated, someone read it top to bottom before deploying. If you cannot read AI-generated code and predict what it does, either break the prompt into smaller pieces or ask the AI to explain it.

### 4.2 Curl before you commit

Every HTTP endpoint we shipped was verified with a literal `curl` from a different host. Not "the code compiles" — "the endpoint returns what it's supposed to return when called from outside." This is the test that distinguishes `changeme` (placeholder that the AI auto-filled) from a real token.

### 4.3 Peer checks across teams

Team 6 (Inspector) probed Team 3 (Analyst) and got a `401` response using the shared `SOC_PROTOCOL_TOKEN`. That was a compliance finding — Analyst had drifted from the protocol. This is peer-review via traffic, not code review.

### 4.4 Read the env, not just the code

Our first live test of Team 5 (Dispatcher) appeared to fail with `401`. We thought their app was broken. Actual cause: their `.env` file said `SOC_PROTOCOL_TOKEN=changeme` while the app loaded `~/.soc_env` with the real token. The code was fine. The config wasn't.

**Lesson:** when a bearer check fails, read both ends of the config, not just the code.

### 4.5 Compile-level static checks

```bash
python3 -m py_compile **/*.py
```

Catches syntax and import errors. Cheap, should run before every deploy. The AI occasionally introduces circular imports when refactoring across files; compilation catches that.

### 4.6 Grep for literals

Before making our repos public, we ran:

```bash
grep -rInE "GhostTrace-0[1-6]!|sk-ant-|changeme|-----BEGIN.*PRIVATE KEY" .
```

Caught ten hardcoded Lightsail passwords in one team's scratch Python scripts — where the AI had "helpfully" inlined the password because the team had pasted it in a prompt earlier. **The AI will not remove secrets it once saw.** You have to scan.

---

## 5. Moments where the AI was wrong and how we caught it

We kept a running journal ([`methodology-journal.md`](methodology-journal.md)). Below are examples from the build day we chose to preserve as teaching moments.

### Moment 1 — The bearer token that did nothing

**Context:** Team 3 (Analyst) asked Claude to "add bearer auth on /ingest." It did. The code looked right. Tests passed.

**What went wrong:** the app read `os.getenv("SIEM_API_KEY", "changeme")` and compared incoming tokens against that. The env var was never set in production, so the app compared against the string `"changeme"`. Any peer sending `Bearer <shared-soc-token>` got `401`. The check was real; the configured value was placeholder.

**How it was caught:** Team 6's probe C-AUTH-002 returned FAIL when sending the shared token. That's the whole reason the Inspector team exists.

**Lesson:** AI will happily write a bearer check that compiles AND passes its own unit tests AND never actually works because the configured secret is a placeholder. Peer testing catches this. Unit testing alone does not.

### Moment 2 — Schema that diverged from the contract

**Context:** Team 3 also modified their `/ingest` request-body model and added a required `source` field that the protocol envelope didn't have. Peer events without that field got `422`.

**What went wrong:** asked to "add additional context" to a model, Claude added a required field. The AI did not know that the envelope was a contract shared across five other peer tools. No one had told it.

**How it was caught:** integration testing showed peers could auth (`200` instead of `401`) but immediately failed with `422`. The fix was trivial; the insight wasn't.

**Lesson:** if your code implements a contract, **say so in every relevant prompt**. Paste the contract doc. Tell the AI "any modification to this model must not add required fields."

### Moment 3 — The admin page that served docs

**Context:** Team 4 (Hunter) shipped an admin page on port 8001. Their probe C-ADMIN-001 passed — 401 without auth — looked great. But then someone noticed `http://wic04:8001/` (bare root) returned 200 OK with 30 KB of HTML.

**What went wrong:** the team built a public "landing page" at `/` that listed their API, and protected only `/admin` with auth. The protocol said "admin page requires auth" — it didn't say anything about `/`. The AI had no reason to put auth on `/`.

**How it was caught:** an ad-hoc curl to the port root. Not by any of the 8 automated probes.

**Lesson:** automated probes catch what you design them to catch. Manual ad-hoc checks catch the rest. Both are needed.

---

## 6. When to stop using AI and think for yourself

There are moments in this kind of work where the AI will slow you down, not speed you up:

1. **When scope is unclear.** "Should this tool do X or Y?" is a decision, not a task. AI gives you reasoning for both; you have to pick. Don't let the AI's tendency toward balanced summaries stop you from deciding.

2. **When you're debugging silently-broken integration.** If curl returns 401 and you don't understand why, staring at the code is faster than prompting. Grep the running process's env vars. Read the live HTTP response with `-i`. Human observability still wins.

3. **When the AI starts looping.** If after three prompts it's still not doing what you want, stop. Rewrite the prompt from scratch with more context. Or switch to writing that piece yourself.

4. **When the security posture is the point.** "Is this auth check actually secure?" is a human question. The AI can help you reason about it, but you own the answer. Our Team 3 bearer-check incident is not a rare case; it's the typical case.

5. **When you're deciding what to ship to production.** The AI is great for drafts. It is a bad judge of "is this good enough?" because it cannot see your operational context. You decide.

---

## 7. A reusable prompt library

See the companion document [`prompt-library.md`](prompt-library.md) — a curated set of prompts we actually used during the workshop, each tagged with what it produced, whether we accepted the output, and what we'd change next time.

---

## 8. Bringing this back to HQ

Suggested teaching sequence for your colleagues:

1. **Demo session (30 min).** Show Claude Code running. Do a trivial task live (scaffold a simple FastAPI app). Not polished; let them see you iterate.
2. **Guided exercise (2 hours).** Each colleague picks one small task — add a new compliance check, translate a document, write a test. They drive, you coach.
3. **First real use (1–2 weeks later).** Each colleague uses Claude Code for one real task in their actual workflow, keeps a journal (exactly as we did), and reports back what worked and what didn't.
4. **Group retrospective (1 hour).** Everyone shares their journal. Identify the patterns that are emerging. Promote the best prompts to a team-shared prompt library.

This is a six-week path from "never heard of Claude Code" to "uses it daily for specific, measurable tasks." Pushing faster than that tends to create resentment or over-reliance. Both are bad outcomes.

---

## 9. Things we didn't try but might have helped

Noted here for honest completeness. If you want to run this exercise again:

- **Pre-scaffold the protocol doc as a prompt.** We could have had every team pre-load the soc-protocol spec into their first Claude session as context. Might have avoided Team 3's schema drift.
- **Shared prompt templates per team.** We gave each team English prompts inline in their plan. If we'd centralized a prompt library (for `/ingest` implementations, admin auth, etc.), divergence would have been smaller.
- **Continuous compliance during the day.** Team 6 produced findings at the end. If they'd produced them hourly, the other teams would have had time to fix.

---

Good luck teaching this. Question every prompt. Cite the journal. Ship the fix.
