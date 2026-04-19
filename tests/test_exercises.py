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


def test_exercise_same_name_different_equipment_allowed(client):
    """同動作名 + 不同器材應視為不同變體（臥推 × 槓鈴 / 啞鈴）。

    曾經的 bug：create_exercise 只檢查 name，導致同名不同器材被 409 擋掉。
    """
    r1 = client.post("/api/exercises", json={"name": "臥推", "equipment": "槓鈴"})
    assert r1.status_code == 201
    r2 = client.post("/api/exercises", json={"name": "臥推", "equipment": "啞鈴"})
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]

    # 但同 name + 同 equipment 仍該被擋下
    r3 = client.post("/api/exercises", json={"name": "臥推", "equipment": "槓鈴"})
    assert r3.status_code == 409


def test_exercise_history_empty(client):
    r = client.post("/api/exercises", json={"name": "硬舉"})
    exercise_id = r.json()["id"]
    r = client.get(f"/api/exercises/{exercise_id}/history")
    assert r.status_code == 200
    assert r.json() == []


def test_exercise_prs_no_sets(client):
    ex_id = client.post("/api/exercises", json={"name": "臥推"}).json()["id"]
    r = client.get(f"/api/exercises/{ex_id}/prs")
    assert r.status_code == 200
    data = r.json()
    assert data["exercise_id"] == ex_id
    assert data["exercise_name"] == "臥推"
    assert data["best_weight"] is None
    assert data["best_1rm"] is None


def test_exercise_prs_best_weight_and_1rm_same_set(client):
    ex_id = client.post("/api/exercises", json={"name": "深蹲"}).json()["id"]
    client.post("/api/workouts", json={
        "sets": [
            {"exercise_id": ex_id, "set_number": 1, "weight": 100.0, "reps": 5},
            {"exercise_id": ex_id, "set_number": 2, "weight": 120.0, "reps": 1},
        ],
    })
    r = client.get(f"/api/exercises/{ex_id}/prs")
    assert r.status_code == 200
    data = r.json()
    # 120×1 → 1RM = 120*(1+1/30)=124.0
    # 100×5 → 1RM = 100*(1+5/30)≈116.7
    # 所以 best_weight 與 best_1rm 都指向 120×1 那組
    assert data["best_weight"]["weight"] == 120.0
    assert data["best_weight"]["reps"] == 1
    assert data["best_1rm"]["weight"] == 120.0
    assert data["best_1rm"]["estimated_1rm"] == 124.0


def test_exercise_prs_best_weight_and_1rm_differ(client):
    ex_id = client.post("/api/exercises", json={"name": "硬舉"}).json()["id"]
    client.post("/api/workouts", json={
        "sets": [
            {"exercise_id": ex_id, "set_number": 1, "weight": 150.0, "reps": 1},  # 1RM = 155.0
            {"exercise_id": ex_id, "set_number": 2, "weight": 120.0, "reps": 10}, # 1RM = 160.0
        ],
    })
    r = client.get(f"/api/exercises/{ex_id}/prs")
    assert r.status_code == 200
    data = r.json()
    assert data["best_weight"]["weight"] == 150.0   # 最重那組
    assert data["best_1rm"]["weight"] == 120.0      # 推估 1RM 最高那組
    assert data["best_1rm"]["estimated_1rm"] == 160.0


def test_exercise_prs_404(client):
    r = client.get("/api/exercises/9999/prs")
    assert r.status_code == 404
