from keel import repo


async def _ctx(conn):
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", "h")
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "s1", [])
    return pid, person, part


async def test_insert_outcome(conn):
    pid, person, part = await _ctx(conn)
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    o = await repo.insert_outcome(conn, decision_id=d["id"], result="held",
                                  evidence_ref="pr#1", source="manual", confirmed_by=person)
    assert o["result"] == "held" and o["source"] == "manual" and o["confirmed_by"] == person


async def test_get_alert_and_feedback(conn):
    pid, person, part = await _ctx(conn)
    d = await repo.insert_decision(conn, project_id=pid, statement="x", rationale="r",
                                   scope_tags=["api:orders"], owner_person_id=person,
                                   source_participant_id=part)
    a = await repo.insert_alert(conn, project_id=pid, target_participant_id=part,
                                target_person_id=person, kind="change", ref_id=d["id"])
    assert (await repo.get_alert(conn, a["id"]))["id"] == a["id"]
    fb = await repo.insert_alert_feedback(conn, alert_id=a["id"], verdict="useful", note="good")
    assert fb["verdict"] == "useful"


async def test_insert_decision_request(conn):
    pid, person, part = await _ctx(conn)
    owner = await repo.upsert_person(conn, pid, "boss", "h2")
    r = await repo.insert_decision_request(conn, project_id=pid, requester_participant_id=part,
                                           owner_person_id=owner, question="cursor or offset?",
                                           options=["cursor", "offset"], scope_tags=["api:orders"])
    assert r["status"] == "open" and r["owner_person_id"] == owner
    assert list(r["options"]) == ["cursor", "offset"]
