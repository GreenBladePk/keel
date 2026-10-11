import pytest
from keel import repo
from keel.principal import Principal
from keel.events import validate_chain
from keel.tools.report_activity import report_activity
import keel.conflict as conflict_pkg
from tests.fakes import ScriptedJudge


async def _ctx(conn):
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", "h")
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "s1", [])
    return pid, person, part


async def test_no_scope_is_none_no_alert(conn, db_pool):
    pid, person, part = await _ctx(conn)
    out = await report_activity(db_pool, Principal(pid, person, "s1"), source="turn")
    assert out["result"] == "none" and out["alert_id"] is None
    assert await conn.fetchval("SELECT count(*) FROM drift_signal WHERE project_id=$1", pid) == 1
    assert await conn.fetchval("SELECT count(*) FROM alert WHERE project_id=$1", pid) == 0


async def test_scope_with_decision_is_possible_and_self_alerts(conn, db_pool):
    pid, person, part = await _ctx(conn)
    await repo.insert_decision(conn, project_id=pid, statement="orders use cursor pagination",
                               rationale="r", scope_tags=["api:orders"], owner_person_id=person,
                               source_participant_id=part)
    out = await report_activity(db_pool, Principal(pid, person, "s1"), source="edit",
                                scope_tags=["api:orders"], summary="touch orders pagination",
                                file_paths=["orders.py"], ref="orders.py")
    assert out["result"] == "possible" and out["alert_id"]
    alerts = await repo.project_pending_alerts(conn, pid)
    assert len(alerts) == 1 and alerts[0]["kind"] == "change"
    assert str(alerts[0]["id"]) == out["alert_id"]
    assert await validate_chain(conn, pid) is True


async def test_conflict_sets_result_and_alert_ref(conn, db_pool, monkeypatch):
    monkeypatch.setattr(conflict_pkg, "get_judge", lambda settings=None: ScriptedJudge())
    pid, person, part = await _ctx(conn)
    from keel.llm.embeddings import DeterministicEmbedder
    emb = await DeterministicEmbedder().embed("orders API uses cursor-based pagination\nr")
    d = await repo.insert_decision(conn, project_id=pid,
                                   statement="orders API uses cursor-based pagination",
                                   rationale="r", scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part, embedding=emb)
    out = await report_activity(db_pool, Principal(pid, person, "s1"), source="edit",
                                scope_tags=["api:orders"],
                                summary="switch orders API to offset pagination",
                                file_paths=["orders.py"], ref="orders.py")
    assert out["result"] == "conflict" and len(out["conflicts"]) == 1
    alerts = await repo.project_pending_alerts(conn, pid)
    assert str(alerts[0]["ref_id"]) == str(d["id"])


async def test_bad_source_errors(conn, db_pool):
    pid, person, part = await _ctx(conn)
    with pytest.raises(ValueError):
        await report_activity(db_pool, Principal(pid, person, "s1"), source="nonsense",
                              scope_tags=["api:orders"])


async def test_unregistered_reporter_errors(conn, db_pool):
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", "h")
    with pytest.raises(LookupError):
        await report_activity(db_pool, Principal(pid, person, "s1"), source="edit",
                              scope_tags=["api:orders"], summary="x")


async def test_report_activity_dedupes_self_alert(conn, db_pool):
    pid, person, part = await _ctx(conn)
    await repo.insert_decision(conn, project_id=pid, statement="orders use cursor pagination",
                               rationale="r", scope_tags=["api:orders"], owner_person_id=person,
                               source_participant_id=part)
    for _ in range(3):
        await report_activity(db_pool, Principal(pid, person, "s1"), source="edit",
                              scope_tags=["api:orders"], summary="touch orders", file_paths=["o.py"])
    # three reports on the same decided scope -> ONE unacked self change-alert, not three
    alerts = await repo.project_pending_alerts(conn, pid)
    assert len(alerts) == 1
    # ...but every call still logs a drift_signal (only the alert is deduped)
    assert await conn.fetchval("SELECT count(*) FROM drift_signal WHERE project_id=$1", pid) == 3
    # after acknowledging, a new report re-alerts (dedupe only suppresses UNACKED)
    part = await repo.get_participant(conn, pid, person, "s1")
    await repo.ack_alert(conn, alerts[0]["id"], part["id"])
    await report_activity(db_pool, Principal(pid, person, "s1"), source="edit",
                          scope_tags=["api:orders"], summary="touch orders again", file_paths=["o.py"])
    assert len(await repo.project_pending_alerts(conn, pid)) == 1  # a fresh one
