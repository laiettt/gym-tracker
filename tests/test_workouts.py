def _make_exercise(client, name="深蹲"):
    return client.post("/api/exercises", json={"name": name}).json()["id"]


def test_create_workout_with_sets(client):
    ex_id = _make_exercise(client)
    r = client.post("/api/workouts", json={
        "sets": [
            {"exercise_id": ex_id, "set_number": 1, "weight": 100, "reps": 5},
            {"exercise_id": ex_id, "set_number": 2, "weight": 100, "reps": 5},
        ],
    })
    assert r.status_code == 201
    w = r.json()
    assert len(w["sets"]) == 2
    assert w["duration_minutes"] is None


def test_add_set_to_existing_workout(client):
    ex_id = _make_exercise(client)
    w = client.post("/api/workouts", json={"sets": []}).json()
    r = client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": ex_id, "set_number": 1, "weight": 80, "reps": 8,
    })
    assert r.status_code == 201
    assert r.json()["reps"] == 8


def test_add_set_with_null_reps_is_failure(client):
    ex_id = _make_exercise(client)
    w = client.post("/api/workouts", json={"sets": []}).json()
    r = client.post(f"/api/workouts/{w['id']}/sets", json={
        "exercise_id": ex_id, "set_number": 1, "weight": 20, "reps": None,
    })
    assert r.status_code == 201
    assert r.json()["reps"] is None


def test_patch_workout_duration(client):
    w = client.post("/api/workouts", json={"sets": []}).json()
    r = client.patch(f"/api/workouts/{w['id']}", json={"duration_minutes": 45})
    assert r.status_code == 200
    assert r.json()["duration_minutes"] == 45


def test_reorder_sets(client):
    ex_id = _make_exercise(client)
    w = client.post("/api/workouts", json={
        "sets": [
            {"exercise_id": ex_id, "set_number": 1, "weight": 100, "reps": 5},
            {"exercise_id": ex_id, "set_number": 2, "weight": 110, "reps": 3},
            {"exercise_id": ex_id, "set_number": 3, "weight": 90, "reps": 8},
        ],
    }).json()
    ids = [s["id"] for s in w["sets"]]
    reversed_ids = list(reversed(ids))

    r = client.post(f"/api/workouts/{w['id']}/sets/reorder",
                    json={"set_ids": reversed_ids})
    assert r.status_code == 200
    new_sets = sorted(r.json()["sets"], key=lambda s: s["set_number"])
    assert [s["id"] for s in new_sets] == reversed_ids


def test_reorder_sets_rejects_mismatch(client):
    ex_id = _make_exercise(client)
    w = client.post("/api/workouts", json={
        "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 50, "reps": 5}],
    }).json()
    r = client.post(f"/api/workouts/{w['id']}/sets/reorder",
                    json={"set_ids": [999]})
    assert r.status_code == 400


def test_delete_workout_cascades_sets(client):
    ex_id = _make_exercise(client)
    w = client.post("/api/workouts", json={
        "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 50, "reps": 10}],
    }).json()
    assert client.delete(f"/api/workouts/{w['id']}").status_code == 204
    assert client.get(f"/api/workouts/{w['id']}").status_code == 404
