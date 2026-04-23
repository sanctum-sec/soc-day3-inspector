import asyncio
import importlib
import pkgutil
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx

import probes as probe_pkg
from probes import get_probes, get_slow_probes
from targets import TARGETS
from storage.db import save_finding

# Per-(tool, check_id) last-run timestamp — enforces 60s minimum between runs
_last_run: dict[str, float] = {}


def _load_probe_modules():
    """Import every module under the probes/ package so @register decorators fire."""
    for _, name, _ in pkgutil.iter_modules(probe_pkg.__path__):
        importlib.import_module(f"probes.{name}")


def _can_run(tool: str, check_id: str, min_interval: float = 60.0) -> bool:
    key = f"{tool}:{check_id}"
    now = datetime.now(timezone.utc).timestamp()
    if now - _last_run.get(key, 0) >= min_interval:
        _last_run[key] = now
        return True
    return False


async def _run_probes(probe_list, min_interval: float = 60.0):
    async with httpx.AsyncClient() as client:
        for target in TARGETS:
            for fn in probe_list:
                try:
                    result = await fn(target["host"], client)
                    check_id = result.get("check_id", "C-UNKNOWN")
                    if not _can_run(target["tool"], check_id, min_interval):
                        continue
                    finding = {
                        "finding_id":   f"F-{uuid.uuid4().hex[:8].upper()}",
                        "probe_time":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "target_tool":  target["tool"],
                        "target_host":  target["host"],
                        **result,
                    }
                    await save_finding(finding)
                except Exception as exc:
                    print(f"[scheduler] probe error on {target['tool']}: {exc}")


async def run_regular_probes():
    await _run_probes(get_probes(), min_interval=60.0)


async def run_slow_probes():
    await _run_probes(get_slow_probes(), min_interval=3600.0)


def start_scheduler() -> AsyncIOScheduler:
    _load_probe_modules()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_regular_probes, "interval", seconds=60,  id="regular")
    scheduler.add_job(run_slow_probes,   "interval", seconds=3600, id="slow")
    scheduler.start()
    return scheduler
