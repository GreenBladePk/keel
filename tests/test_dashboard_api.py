import hashlib
import httpx
from keel import repo
from keel.server import app


async def _seed(db_pool):
    async with db_pool.acquire() as conn:
        pid = await repo.upsert_project(conn, "demo")
        person = await repo.upsert_person(conn, pid, "vasan",
                                          hashlib.sha256(b"dev-token").hexdigest())
        part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "s1", [])
        d = await repo.insert_decision(conn, project_id=pid, statement="cursor pagination",
                                       rationale="scales", scope_tags=["api:orders"],
                                       owner_person_id=person, source_participant_id=part)
        await repo.insert_conflict(conn, project_id=pid, decision_a_id=d["id"],
                                   subject_type="decision", subject_ref=str(d["id"]),
                                   relation="contradicts", severity="high", explanation="e")
        await repo.insert_alert(conn, project_id=pid, target_participant_id=part,
                                target_person_id=person, kind="change", ref_id=d["id"])
        await repo.insert_handoff(conn, project_id=pid, from_participant_id=part,
                                  to_person_id=person, to_participant_id=None,
                                  scope_tags=["api:orders"], decision_ids=[], conflict_ids=[],
                                  note="take it")
        from keel.events import append_event
        await append_event(conn, pid, actor="tester", action="decision.recorded",
                           payload={"decision_id": str(d["id"])})
        return pid


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_state_requires_token(db_pool):
    await _seed(db_pool)
    async with _client() as c:
        r = await c.get("/api/state")
    assert r.status_code == 401


async def test_state_returns_project_data(db_pool):
    await _seed(db_pool)
    async with _client() as c:
        r = await c.get("/api/state", headers={"Authorization": "Bearer dev-token",
                                               "X-Keel-Session": "s1"})
    assert r.status_code == 200
    s = r.json()
    assert len(s["active_decisions"]) == 1
    assert s["active_decisions"][0]["statement"] == "cursor pagination"
    assert len(s["open_conflicts"]) == 1 and len(s["pending_alerts"]) == 1
    assert len(s["pending_handoffs"]) == 1


async def test_events_limit_and_shape(db_pool):
    await _seed(db_pool)
    async with _client() as c:
        r = await c.get("/api/events?limit=99999",
                        headers={"Authorization": "Bearer dev-token", "X-Keel-Session": "s1"})
    assert r.status_code == 200
    evs = r.json()["events"]
    assert len(evs) >= 1
    e = evs[0]
    assert {"id", "actor", "action", "payload", "created_at"} <= set(e)
    assert isinstance(e["payload"], dict)


async def test_cors_preflight_no_auth(db_pool):
    await _seed(db_pool)
    async with _client() as c:
        r = await c.options("/api/state", headers={"Origin": "http://localhost:8050",
                                                   "Access-Control-Request-Method": "GET"})
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") in ("*", "http://localhost:8050")


async def test_project_isolation(db_pool):
    await _seed(db_pool)
    async with db_pool.acquire() as conn:
        other = await repo.upsert_project(conn, "other")
        await repo.upsert_person(conn, other, "x", hashlib.sha256(b"other-token").hexdigest())
    async with _client() as c:
        r = await c.get("/api/state", headers={"Authorization": "Bearer other-token",
                                               "X-Keel-Session": "s1"})
    assert r.status_code == 200
    s = r.json()
    assert s["active_decisions"] == [] and s["open_conflicts"] == []
