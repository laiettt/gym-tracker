def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_exercise_crud(client):
    r = client.post("/api/exercises", json={"name": "深蹲", "category": "腿"})
    assert r.status_code == 201
    ex = r.json()
    assert ex["name"] == "深蹲"
    exercise_id = ex["id"]

    r = client.get("/api/exercises")
    assert r.status_code == 200
    assert any(e["id"] == exercise_id for e in r.json())

    r = client.patch(f"/api/exercises/{exercise_id}", json={"category": "下肢"})
    assert r.status_code == 200
    assert r.json()["category"] == "下肢"

    r = client.delete(f"/api/exercises/{exercise_id}")
    assert r.status_code == 204

    r = client.get(f"/api/exercises/{exercise_id}")
    assert r.status_code == 404


def test_exercise_name_unique(client):
    client.post("/api/exercises", json={"name": "臥推"})
    r = client.post("/api/exercises", json={"name": "臥推"})
    assert r.status_code >= 400


def test_exercise_history_empty(client):
    r = client.post("/api/exercises", json={"name": "硬舉"})
    exercise_id = r.json()["id"]
    r = client.get(f"/api/exercises/{exercise_id}/history")
    assert r.status_code == 200
    assert r.json() == []
