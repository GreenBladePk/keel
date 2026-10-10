"""Seed the Keel demo DB (keel_demo): project + two people/tokens, clean ledger,
and pre-seed the judgment cache for the canonical contradiction so the conflict
beat is instant on stage. Reads no secrets. Idempotent.

Run from the keel/ repo root:  python demo/seed.py
"""
import asyncio
import hashlib

import asyncpg

from keel.db import pool as db
from keel import repo
from keel.conflict.cache import cache_key, put_cached
from keel.conflict.judge import Judgment

ADMIN_DSN = "postgresql://keel:keel@localhost:5433/postgres"
DEMO_DSN = "postgresql://keel:keel@localhost:5433/keel_demo"
DEMO_MODEL = "openai/gpt-4.1-mini"  # must match KEEL_LLM_MODEL used on stage

# Canonical texts the runbook tells the presenter to use. Priming the cache for
# these makes Beat 2/3 instant even on a bad venue network; live Claude phrasings
# that differ simply fall through to a (fast) live RouterPlus call.
CURSOR_STMT = "The orders API uses cursor-based pagination"
CURSOR_RATIONALE = "cursors scale better than offset for large tables"
CANDIDATE_TEXT = f"{CURSOR_STMT}\n{CURSOR_RATIONALE}"
OFFSET_STMT = "Switch the orders API to offset-based pagination with page numbers"
OFFSET_RATIONALE = "simpler for clients"
# Beat 2 (record_decision) subject text = statement\nrationale; Beat 3
# (check_intent / PreToolUse) subject text = the planned edit. Prime both.
SUBJECTS = [
    f"{OFFSET_STMT}\n{OFFSET_RATIONALE}",
    "Switch the orders API to offset-based pagination with page numbers",
    "switch the orders API to offset pagination",
    "use offset pagination with page and page_size for the orders API",
]
_VERDICT = Judgment(relation="contradicts", confidence=0.9,
                    explanation=("The proposed offset/page-number pagination contradicts the "
                                 "active decision that the orders API uses cursor-based pagination."),
                    evidence=CURSOR_STMT)


async def _ensure_db():
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname='keel_demo'")
        if not exists:
            await conn.execute("CREATE DATABASE keel_demo")
            print("created database keel_demo")
    finally:
        await conn.close()


_TABLES = ("judgment_cache", "alert_feedback", "alert", "drift_signal", "decision_request",
           "outcome", "handoff", "conflict", "claim", "dependency", "event", "decision",
           "goal", "participant", "person", "project")


async def main():
    await _ensure_db()
    pool = await db.init_pool(DEMO_DSN)
    async with pool.acquire() as c:
        await db.apply_schema(c)
        await c.execute("TRUNCATE " + ", ".join(_TABLES) + " RESTART IDENTITY CASCADE")
        pid = await repo.upsert_project(c, "demo")
        alice = await repo.upsert_person(c, pid, "alice", hashlib.sha256(b"alice-token").hexdigest())
        bob = await repo.upsert_person(c, pid, "bob", hashlib.sha256(b"bob-token").hexdigest())
        for subj in SUBJECTS:
            await put_cached(c, cache_key(DEMO_MODEL, subj, CANDIDATE_TEXT), DEMO_MODEL, _VERDICT)
    await db.close_pool()
    print("seeded project 'demo' | people: alice, bob | cache primed |",
          f"people ids: alice={alice} bob={bob}")
    print("tokens: alice-token / bob-token")


if __name__ == "__main__":
    asyncio.run(main())
