import pytest
from keel import repo
from keel.principal import Principal
from keel.events import validate_chain
from keel.tools.outcomes import record_outcome, rate_alert
from keel.tools.decision_request import request_decision


async def _ctx(conn):
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", "h")
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "s1", [])
    return pid, person, part


async def test_record_outcome_ok(conn, db_pool):
    pid, person, part = await _ctx(conn)
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    out = await record_outcome(db_pool, Principal(pid, person, "s1"),
                               decision_id=str(d["id"]), result="held", evidence_ref="pr#1")
    assert out["outcome_id"]
    row = await conn.fetchrow("SELECT * FROM outcome WHERE id=$1", out["outcome_id"])
    assert row["result"] == "held" and row["source"] == "manual" and row["confirmed_by"] == person
    assert await validate_chain(conn, pid) is True


async def test_record_outcome_bad_result(conn, db_pool):
    pid, person, part = await _ctx(conn)
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    with pytest.raises(ValueError):
        await record_outcome(db_pool, Principal(pid, person, "s1"),
                             decision_id=str(d["id"]), result="nope")


async def test_record_outcome_foreign_decision(conn, db_pool):
    pid, person, part = await _ctx(conn)
    other = await repo.upsert_project(conn, "other")
    operson = await repo.upsert_person(conn, other, "x", "h3")
    opart = await repo.upsert_participant(conn, other, operson, "cc", "deep", "os", [])
    foreign = await repo.insert_decision(conn, project_id=other, statement="f", rationale="r",
                                         scope_tags=["api:orders"], owner_person_id=operson,
                                         source_participant_id=opart)
    with pytest.raises(ValueError):
        await record_outcome(db_pool, Principal(pid, person, "s1"),
                             decision_id=str(foreign["id"]), result="held")


async def test_record_outcome_malformed_id(conn, db_pool):
    pid, person, part = await _ctx(conn)
    with pytest.raises(LookupError):
        await record_outcome(db_pool, Principal(pid, person, "s1"),
                             decision_id="not-a-uuid", result="held")


async def test_rate_alert_ok(conn, db_pool):
    pid, person, part = await _ctx(conn)
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    a = await repo.insert_alert(conn, project_id=pid, target_participant_id=part,
                                target_person_id=person, kind="change", ref_id=d["id"])
    out = await rate_alert(db_pool, Principal(pid, person, "s1"),
                           alert_id=str(a["id"]), verdict="useful", note="helped")
    assert out["feedback_id"]
    assert await conn.fetchval("SELECT verdict FROM alert_feedback WHERE id=$1",
                               out["feedback_id"]) == "useful"


async def test_rate_alert_not_mine(conn, db_pool):
    pid, person, part = await _ctx(conn)
    other = await repo.upsert_person(conn, pid, "mate", "h2")
    opart = await repo.upsert_participant(conn, pid, other, "cc", "deep", "s2", [])
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    a = await repo.insert_alert(conn, project_id=pid, target_participant_id=opart,
                                target_person_id=other, kind="change", ref_id=d["id"])
    with pytest.raises(PermissionError):
        await rate_alert(db_pool, Principal(pid, person, "s1"),
                         alert_id=str(a["id"]), verdict="noise")
    assert await conn.fetchval("SELECT count(*) FROM alert_feedback") == 0


async def test_rate_alert_bad_verdict(conn, db_pool):
    pid, person, part = await _ctx(conn)
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    a = await repo.insert_alert(conn, project_id=pid, target_participant_id=part,
                                target_person_id=person, kind="change", ref_id=d["id"])
    with pytest.raises(ValueError):
        await rate_alert(db_pool, Principal(pid, person, "s1"),
                         alert_id=str(a["id"]), verdict="meh")


async def test_request_decision_ok(conn, db_pool):
    pid, person, part = await _ctx(conn)
    await repo.upsert_person(conn, pid, "boss", "h2")
    out = await request_decision(db_pool, Principal(pid, person, "s1"),
                                 question="cursor or offset?", owner_person="boss",
                                 options=["cursor", "offset"], scope_tags=["API: Orders"])
    assert out["status"] == "open" and out["request_id"]
    row = await conn.fetchrow("SELECT * FROM decision_request WHERE id=$1", out["request_id"])
    assert row["question"] == "cursor or offset?" and list(row["scope_tags"]) == ["api:orders"]
    assert await validate_chain(conn, pid) is True


async def test_request_decision_unknown_owner(conn, db_pool):
    pid, person, part = await _ctx(conn)
    with pytest.raises(LookupError):
        await request_decision(db_pool, Principal(pid, person, "s1"),
                               question="q?", owner_person="ghost")


async def test_request_decision_empty_question(conn, db_pool):
    pid, person, part = await _ctx(conn)
    await repo.upsert_person(conn, pid, "boss", "h2")
    with pytest.raises(ValueError):
        await request_decision(db_pool, Principal(pid, person, "s1"),
                               question="   ", owner_person="boss")
