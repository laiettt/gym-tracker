"""匯出 / 匯入 API 的測試。"""


def _make_exercise(client, name="深蹲", category="腿"):
    return client.post("/api/exercises", json={"name": name, "category": category}).json()["id"]


def test_export_empty(client):
    r = client.get("/api/export")
    assert r.status_code == 200
    data = r.json()
    assert data["exercises"] == []
    assert data["workouts"] == []
    assert data["routines"] == []


def test_export_includes_all_data(client):
    ex_id = _make_exercise(client, "深蹲", "腿")
    client.post("/api/workouts", json={
        "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 100.0, "reps": 5}],
    })
    client.post("/api/routines", json={
        "name": "PPL",
        "exercises": [{"exercise_id": ex_id, "order_index": 0, "target_sets": 3, "target_reps": 5}],
    })

    r = client.get("/api/export")
    assert r.status_code == 200
    data = r.json()

    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "深蹲"
    assert data["exercises"][0]["category"] == "腿"

    assert len(data["workouts"]) == 1
    assert len(data["workouts"][0]["sets"]) == 1
    assert data["workouts"][0]["sets"][0]["exercise_name"] == "深蹲"
    assert data["workouts"][0]["sets"][0]["weight"] == 100.0

    assert len(data["routines"]) == 1
    assert data["routines"][0]["name"] == "PPL"
    assert data["routines"][0]["exercises"][0]["exercise_name"] == "深蹲"


def test_import_new_exercises(client):
    payload = {
        "exercises": [{"name": "臥推", "category": "胸"}],
        "workouts": [],
        "routines": [],
    }
    r = client.post("/api/import", json=payload)
    assert r.status_code == 200
    assert r.json()["imported"]["exercises"] == 1

    exercises = client.get("/api/exercises").json()
    assert any(e["name"] == "臥推" for e in exercises)


def test_import_skips_duplicate_exercises(client):
    _make_exercise(client, "深蹲")  # 先建好

    payload = {
        "exercises": [{"name": "深蹲"}],  # 重複
        "workouts": [],
        "routines": [],
    }
    r = client.post("/api/import", json=payload)
    assert r.status_code == 200
    assert r.json()["imported"]["exercises"] == 0

    # 確認沒有重複
    exercises = client.get("/api/exercises").json()
    assert sum(1 for e in exercises if e["name"] == "深蹲") == 1


def test_export_import_roundtrip(client):
    ex_id = _make_exercise(client, "深蹲", "腿")
    client.post("/api/workouts", json={
        "sets": [{"exercise_id": ex_id, "set_number": 1, "weight": 100.0, "reps": 5}],
    })
    client.post("/api/routines", json={
        "name": "腿日",
        "exercises": [{"exercise_id": ex_id, "order_index": 0, "target_sets": 4, "target_reps": 6}],
    })

    export_data = client.get("/api/export").json()

    # 匯入相同資料（動作跳過，訓練 / 課表新增）
    r = client.post("/api/import", json=export_data)
    assert r.status_code == 200
    result = r.json()
    assert result["imported"]["exercises"] == 0   # 深蹲已存在
    assert result["imported"]["workouts"] == 1
    assert result["imported"]["routines"] == 1

    # 動作庫數量不變
    assert len(client.get("/api/exercises").json()) == 1
    # 訓練記錄增加了一筆
    assert len(client.get("/api/workouts").json()) == 2
