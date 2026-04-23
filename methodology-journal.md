# Methodology Journal — Team 6 Inspector

> Keep this updated throughout the day. Every prompt you give Claude goes here with a one-line note.
> This is the raw material for the `ai-assisted-build-methodology` training document.

---

## Format

```
### [HH:MM] Phase N — Short description
**Prompt:**
> paste prompt here

**Result:** one-line summary of what Claude generated
**Accepted:** yes / partially / no
**Changed:** what we modified and why
```

---

## Entries

### [09:30] Phase 1 — Initial scaffold

**Prompt:**
> Start a FastAPI project in ~/app for a SOC compliance inspection tool. Create main.py, probes/__init__.py, storage/db.py, schemas/envelope.py, targets.py, scheduler.py, templates/compliance.html, admin app on port 8001, systemd unit, requirements.txt.

**Result:** Full scaffold with all files — FastAPI app, SQLite storage, HTMX dashboard, Basic Auth admin page, APScheduler probe runner.
**Accepted:** yes — deployed directly to server
**Changed:** None at scaffold stage — verified each file before deploying

---

_Continue adding entries below as the day progresses..._
