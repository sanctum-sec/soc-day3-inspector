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
from storage.db import save_finding, get_compliance_matrix

_last_run: dict[str, float] = {}

# All checks except C-RATE-001 — used to decide when a team is "all green"
_REGULAR_CHECK_IDS = {
    "C-LIVE-001", "C-AUTH-001", "C-AUTH-002",
    "C-SCHEMA-001", "C-SCHEMA-002",
    "C-ADMIN-001", "C-ISOLATION-001",
}


def _load_probe_modules():
    for _, name, _ in pkgutil.iter_modules(probe_pkg.__path__):
        importlib.import_module(f"probes.{name}")


def _can_run(tool: str, check_id: str, min_interval: float = 15.0) -> bool:
    key = f"{tool}:{check_id}"
    now = datetime.now(timezone.utc).timestamp()
    if now - _last_run.get(key, 0) >= min_interval:
        _last_run[key] = now
        return True
    return False


async def _run_one(client: httpx.AsyncClient, target: dict, fn, min_interval: float):
    try:
        result = await fn(target["host"], client)
        check_id = result.get("check_id", "C-UNKNOWN")
        if not _can_run(target["tool"], check_id, min_interval):
            return
        finding = {
            "finding_id":  f"F-{uuid.uuid4().hex[:8].upper()}",
            "probe_time":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "target_tool": target["tool"],
            "target_host": target["host"],
            **result,
        }
        await save_finding(finding)
    except Exception as exc:
        print(f"[scheduler] {target['tool']} probe error: {exc}")


async def _run_probes(probe_list, min_interval: float, targets=None):
    semaphore = asyncio.Semaphore(20)
    async with httpx.AsyncClient() as client:
        async def bounded(target, fn):
            async with semaphore:
                await _run_one(client, target, fn, min_interval)
        tasks = [
            bounded(target, fn)
            for target in (targets or TARGETS)
            for fn in probe_list
        ]
        await asyncio.gather(*tasks)


async def _trigger_rate_limit_for_passing_teams():
    """After each regular cycle, run C-RATE-001 for any team that is
    all-green on every other check. Rate-limited to once per hour."""
    slow = get_slow_probes()
    if not slow:
        return
    matrix = await get_compliance_matrix()
    passing_targets = [
        t for t in TARGETS
        if all(
            matrix.get(t["tool"], {}).get(c, {}).get("status") == "PASS"
            for c in _REGULAR_CHECK_IDS
        )
    ]
    if passing_targets:
        tools = [t["tool"] for t in passing_targets]
        print(f"[scheduler] all-green teams — running C-RATE-001 for: {tools}")
        await _run_probes(slow, min_interval=3600.0, targets=passing_targets)


async def run_regular_probes():
    await _run_probes(get_probes(), min_interval=15.0)
    await _trigger_rate_limit_for_passing_teams()


def start_scheduler() -> AsyncIOScheduler:
    _load_probe_modules()
    scheduler = AsyncIOScheduler()
    now = datetime.now(timezone.utc)
    scheduler.add_job(run_regular_probes, "interval", seconds=15, id="regular",
                      max_instances=2, next_run_time=now)
    scheduler.start()
    return scheduler
