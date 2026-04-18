def test_create_routine_with_exercises(client):
    ex1 = client.post("/api/exercises", json={"name": "臥推"}).json()["id"]
    ex2 = client.post("/api/exercises", json={"name": "肩推"}).json()["id"]
    r = client.post("/api/routines", json={
        "name": "Push Day",
        "description": "胸肩三頭",
        "exercises": [
            {"exercise_id": ex1, "order_index": 0, "target_sets": 4, "target_reps": 8},
            {"exercise_id": ex2, "order_index": 1, "target_sets": 3, "target_reps": 10},
        ],
    })
    assert r.status_code == 201
    routine = r.json()
    assert routine["name"] == "Push Day"
    assert len(routine["routine_exercises"]) == 2


def test_list_and_delete_routine(client):
    r = client.post("/api/routines", json={"name": "Pull Day"})
    routine_id = r.json()["id"]

    assert any(x["id"] == routine_id for x in client.get("/api/routines").json())
    assert client.delete(f"/api/routines/{routine_id}").status_code == 204
    assert client.get(f"/api/routines/{routine_id}").status_code == 404
