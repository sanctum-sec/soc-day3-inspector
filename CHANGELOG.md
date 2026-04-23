# Changelog

All notable changes to this repository. Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [post-workshop] — 2026-04-23

Post-workshop consolidation and publication pass. Everything below was done by the
workshop facilitator after the teams departed — the intent was to capture the team's
production state, redact anything unsafe for a public repo, and give the repo a
permanent shape future readers can use.

### Added

- `README.md` rewritten to describe what the team actually shipped — file layout, services, how to run locally, and a pointer to the shared protocol.
- `PLAN.en.md` / `PLAN.uk.md` — the original Day 3 build plan preserved (bilingual). These used to be the repo's README before the production code landed.
- `.gitignore` — standard Python/SQLite/log excludes.
- `CHANGELOG.md` — this file.

### Changed

- Production code imported from the team's Lightsail (`sudo tar cz` → stream → `tar xz`), excluding `.git`, `__pycache__`, virtualenvs, logs, SQLite databases, and `.env` files.
- The repo now reflects the **final state of production** at workshop close, not just the plan document.

### Security

- Hardcoded Basic Auth credentials (`wic / stepup-krakow-2026`) scrubbed from `PLAN.en.md` / `PLAN.uk.md` — replaced with "ask the instructor."
- Workshop deploy key (SSH, write-scope on this repo) was **revoked** after the workshop closed.
- GitHub Actions secrets set during the workshop (`LIGHTSAIL_HOST`, `LIGHTSAIL_PASSWORD`, `SOC_PROTOCOL_TOKEN`) were **removed** from the repo's secret store.

### Administrative

- Repository visibility flipped from **private** to **public** on 2026-04-23 as part of the workshop's open-share commitment.
- Pre-publication secret scan run on the repo: no credential patterns remain in current tree (git history still contains the original commits made during the workshop).
- Production box (`wic06.sanctumsec.com`) now runs from a git checkout of `main`; future updates propagate via `git fetch && git reset --hard origin/main`.


### Inspector-specific additions (post-workshop — the take-home training pack)

The original plan called for seven take-home documents; only the methodology-journal
scaffolding was completed during the day. The remaining six were authored post-workshop
based on the actual build events, the probe source code, and the workshop retrospective:

- `inspection-checklist.en.md` — regulator-facing 8-check audit with manual `curl` commands, expected results, failure implications
- `inspection-checklist.uk.md` — full Ukrainian translation
- `how-to-inspect-a-soc.uk.md` — narrative runbook for a regulator arriving at a SOC
- `ai-assisted-build-methodology.en.md` — the HQ teaching doc (prompt patterns that worked, three documented "AI was wrong" moments, verification techniques, 6-week rollout plan)
- `ai-assisted-build-methodology.uk.md` — full Ukrainian translation
- `prompt-library.md` — curated real prompts from the build, tagged recommended / careful / avoid
- `lessons-learned.uk.md` — honest retrospective in Ukrainian, citing concrete incidents


---

## [0.1.0] — 2026-04-23 (workshop build day)

**Team 6 — Inspector (Інспектор)** shipped during the STEP UP 3! Women's Cyber
Defense Workshop in Kraków (10:45–16:30 CET).

### Summary

Built a compliance inspection tool that probes the five other SOC tools against the declared contract every 60 seconds, plus a take-home bilingual training pack for regulators returning to HQ. Dual deliverable — tool plus teaching asset.

### Shipped to production on `wic06.sanctumsec.com` (deployed at `/home/ubuntu/app/`)

- `main.py` — FastAPI app (`/compliance`, `/findings`, `/compliance-partial`)
- `scheduler.py` — APScheduler; probes every 60s
- `probes/` — 8 probe modules (liveness, auth-noheader, auth-wrongtoken, schema-nonjson, schema-missingfield, rate-limit, admin-noauth, admin-isolation)
- `targets.py` — registry of the 5 peer tools
- `storage/` — SQLite findings store
- `schemas/` — event envelope
- `admin/` — port-8001 admin dashboard
- `templates/` — Jinja: `compliance.html`, `compliance_partial.html`
- `methodology-journal.md` — one journal entry from the scaffold phase
- `inspector.service` — systemd unit
- `start.sh` — quick-start helper

### Notes from build day

- Built almost entirely with Claude Code over ~6 hours, following the Day-3 plan
  preserved in `PLAN.en.md` / `PLAN.uk.md`.
- Implements the shared contract in [`sanctum-sec/soc-protocol`](https://github.com/sanctum-sec/soc-protocol).
- Running on a `medium_3_0` Lightsail instance in `eu-central-1` (Frankfurt).

---

## [0.0.1] — 2026-04-22 (repo initialised)

- Repo created with the Day-3 team plan as `README.md` + `README.en.md` (English and
  Ukrainian versions).
- GitHub Actions secrets set: `LIGHTSAIL_HOST`, `LIGHTSAIL_PASSWORD`, `SOC_PROTOCOL_TOKEN`.
- Deploy key installed on the team's Lightsail.
- Discussions enabled.
