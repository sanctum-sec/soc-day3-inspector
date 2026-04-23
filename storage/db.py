import aiosqlite
import uuid
from datetime import datetime

DB_PATH = "/home/ubuntu/app/findings.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS findings (
    finding_id   TEXT PRIMARY KEY,
    probe_time   TEXT NOT NULL,
    target_tool  TEXT NOT NULL,
    target_host  TEXT NOT NULL,
    check_id     TEXT NOT NULL,
    check_label  TEXT NOT NULL,
    expected     TEXT NOT NULL,
    observed     TEXT NOT NULL,
    status       TEXT NOT NULL,
    severity     TEXT NOT NULL,
    notes        TEXT
);
"""

CREATE_IDX = "CREATE INDEX IF NOT EXISTS idx_tool_check ON findings(target_tool, check_id, probe_time);"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE)
        await db.execute(CREATE_IDX)
        await db.commit()


async def save_finding(finding: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR REPLACE INTO findings
               (finding_id, probe_time, target_tool, target_host,
                check_id, check_label, expected, observed, status, severity, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                finding["finding_id"],
                finding["probe_time"],
                finding["target_tool"],
                finding["target_host"],
                finding["check_id"],
                finding["check_label"],
                str(finding["expected"]),
                str(finding["observed"]),
                finding["status"],
                finding["severity"],
                finding.get("notes", ""),
            ),
        )
        await db.commit()


async def get_recent_findings(limit: int = 50) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM findings ORDER BY probe_time DESC LIMIT ?", (limit,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_compliance_matrix() -> dict:
    """Returns {tool: {check_id: finding_dict}} — latest result per (tool, check)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT f.* FROM findings f
            JOIN (
                SELECT target_tool, check_id, MAX(probe_time) AS mt
                FROM findings GROUP BY target_tool, check_id
            ) latest
            ON f.target_tool = latest.target_tool
               AND f.check_id  = latest.check_id
               AND f.probe_time = latest.mt
        """) as cur:
            matrix: dict = {}
            for row in await cur.fetchall():
                r = dict(row)
                matrix.setdefault(r["target_tool"], {})[r["check_id"]] = r
            return matrix


async def get_admin_stats() -> dict:
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async def count(where: str, params: tuple = ()):
            async with db.execute(f"SELECT COUNT(*) FROM findings WHERE {where}", params) as c:
                return (await c.fetchone())[0]

        return {
            "checks_5m":  await count("probe_time > datetime('now','-5 minutes')"),
            "checks_1h":  await count("probe_time > datetime('now','-1 hour')"),
            "checks_24h": await count("probe_time > datetime('now','-24 hours')"),
            "fails_today": await count("status='FAIL' AND probe_time > datetime('now','-24 hours')"),
        }
