# Team 6 — Inspector (Інспектор)

> Production SOC tool delivered at **STEP UP 3! Women's Cyber Defense Workshop** (Kraków, 21–23 April 2026) — part of a 6-team live exercise that built a working Security Operations Center in one day.

## What the team built

Regulatory-audit team — continuously inspects the 5 SOC tools against the declared contract, publishes a live compliance dashboard, and produces bilingual take-home training materials on how the build was done with AI.

## Deployed services

| Service | Role |
| --- | --- |
| `inspector.service` | FastAPI app on port 8000 (compliance dashboard + probe scheduler) |

Ran in production on **`wic06.sanctumsec.com`**.

## Repo layout

| Path | What's there |
| --- | --- |
| `main.py` | FastAPI app, `/compliance`, `/findings`, `/compliance-partial` (HTMX) |
| `scheduler.py` | runs probes every 60s |
| `probes/` | one module per compliance check (liveness, auth, schema, rate-limit, admin isolation) |
| `targets.py` | registry of peer tools to probe |
| `storage/` | SQLite findings store |
| `schemas/` | event-envelope models |
| `admin/` | port-8001 admin dashboard |
| `templates/` | Jinja: `compliance.html`, `compliance_partial.html` |
| `methodology-journal.md` | the team's running log of every Claude prompt they used — the take-home teaching asset |
| `start.sh` | quick-start script |

## Running it locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# Admin UI (if present) on port 8001 — see the team's service files
```

Required env vars (set in a local `.env` or `~/.soc_env`):

- `SOC_PROTOCOL_TOKEN` — shared bearer token used between peer SOC tools
- `ADMIN_USER` / `ADMIN_PASS` — admin page HTTP Basic credentials (if this team has an admin UI)

## Protocol implemented

This tool implements the contract defined in **[sanctum-sec/soc-protocol](https://github.com/sanctum-sec/soc-protocol)** — event envelope, bearer-token auth, MITRE ATT&CK tagging, per-port convention (8000 app / 8001 admin).

## Notes from the build day

- This is the team whose final deliverable was *both* the running tool AND the bilingual training package
- `methodology-journal.md` is especially valuable — it's the real raw material from the regulators' build day

## Day 3 build plan (archival)

The original build plan that guided the team during the workshop is preserved here:

- 🇬🇧 [`PLAN.en.md`](PLAN.en.md)
- 🇺🇦 [`PLAN.uk.md`](PLAN.uk.md)

The plans include a cross-cutting AI-CTI goals section covering Modules 4–6 of the Day 3 curriculum (AI-augmented CTI, AI-enabled attack patterns, AI social engineering).
