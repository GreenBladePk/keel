from keel import repo


async def test_insert_drift_signal_roundtrip(conn):
    pid = await repo.upsert_project(conn, "demo")
    person = await repo.upsert_person(conn, pid, "vasan", "h")
    part = await repo.upsert_participant(conn, pid, person, "cc", "deep", "s1", [])
    sig = await repo.insert_drift_signal(conn, project_id=pid, participant_id=part,
                                         source="edit", scope_tags=["api:orders"],
                                         summary="edited pagination", file_paths=["a.py"],
                                         ref="a.py", confidence=0.9, result="conflict")
    assert sig["source"] == "edit" and sig["result"] == "conflict"
    assert list(sig["scope_tags"]) == ["api:orders"] and list(sig["file_paths"]) == ["a.py"]
    assert sig["confidence"] == 0.9
