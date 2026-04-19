"""FastAPI application entry point."""
import base64
import os
import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app import models
from app.database import SessionLocal, engine
from app.routers import exercises, workouts, routines, data, analytics

# 建立資料表（開發階段用，正式環境會用 Alembic migration）
models.Base.metadata.create_all(bind=engine)


def _ensure_exercise_equipment_column() -> None:
    """舊版 gym.db 沒有 exercises.equipment 欄位時補上。

    開發階段沒接 Alembic，又不想每次改欄位都刪 DB；這裡用 SQLAlchemy inspector
    比對 schema，缺欄位就 ALTER TABLE 加一欄（SQLite 支援加 nullable 欄位）。
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("exercises")}
    if "equipment" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE exercises ADD COLUMN equipment VARCHAR(50)"))


#: 早期把器材寫進動作名稱（"槓鈴臥推"），現在改成 name + equipment 兩欄分開。
#: 此表僅處理預設動作；使用者自訂動作不動。
_LEGACY_NAME_RENAMES: dict[str, str] = {
    "槓鈴臥推": "臥推",
    "啞鈴臥推": "臥推",
    "上斜槓鈴臥推": "上斜臥推",
    "上斜啞鈴臥推": "上斜臥推",
    "蝴蝶機夾胸": "夾胸",
    "Cable 夾胸": "夾胸",
    "槓鈴划船": "划船",
    "啞鈴單手划船": "單手划船",
    "啞鈴肩推": "肩推",
    "槓鈴彎舉": "二頭彎舉",
}


def _migrate_exercise_schema() -> None:
    """處理動作庫兩項結構變更：

    1. 移除 exercises.name 上的單欄 unique index（改用 (name, equipment) 複合）。
    2. 把舊的「器材混在名稱裡」動作重新命名（例：槓鈴臥推 → 臥推）。
    """
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    with engine.begin() as conn:
        # 移除舊的 name unique index（SQLAlchemy 生成的名稱為 ix_exercises_name）
        for idx in inspector.get_indexes("exercises"):
            if idx["column_names"] == ["name"] and idx.get("unique"):
                conn.execute(text(f'DROP INDEX IF EXISTS "{idx["name"]}"'))
        # 重建普通索引（非 unique）方便查詢
        existing_idx_names = {i["name"] for i in inspector.get_indexes("exercises")}
        if "ix_exercises_name" not in existing_idx_names:
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_exercises_name ON exercises(name)'))
        # 複合 unique（SQLite 多筆 NULL equipment 視為不同，符合我們需求）
        conn.execute(text(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_exercise_name_equipment '
            'ON exercises(name, equipment)'
        ))

        # 重命名舊預設動作
        for old_name, new_name in _LEGACY_NAME_RENAMES.items():
            row = conn.execute(
                text("SELECT id, equipment FROM exercises WHERE name = :n"),
                {"n": old_name},
            ).first()
            if not row:
                continue
            # 若新名稱 + 同器材已存在，直接刪掉舊的（避免 unique 衝突）
            existing = conn.execute(
                text("SELECT id FROM exercises WHERE name = :n AND equipment IS :e"),
                {"n": new_name, "e": row.equipment},
            ).first()
            if existing:
                # 把引用舊 id 的 set 轉移到新 id
                conn.execute(
                    text("UPDATE sets SET exercise_id = :new WHERE exercise_id = :old"),
                    {"new": existing.id, "old": row.id},
                )
                conn.execute(
                    text("UPDATE routine_exercises SET exercise_id = :new WHERE exercise_id = :old"),
                    {"new": existing.id, "old": row.id},
                )
                conn.execute(text("DELETE FROM exercises WHERE id = :id"), {"id": row.id})
            else:
                conn.execute(
                    text("UPDATE exercises SET name = :n WHERE id = :id"),
                    {"n": new_name, "id": row.id},
                )


_ensure_exercise_equipment_column()
_migrate_exercise_schema()


#: 常見健身動作的預設清單：(name, category, equipment)。
#: 新增動作時若同名已存在只會補 equipment，不會覆蓋使用者自訂的分類。
DEFAULT_EXERCISES: list[tuple[str, str, str | None]] = [
    # 胸
    ("臥推", "胸", "槓鈴"),
    ("臥推", "胸", "啞鈴"),
    ("上斜臥推", "胸", "槓鈴"),
    ("上斜臥推", "胸", "啞鈴"),
    ("夾胸", "胸", "器械"),
    ("夾胸", "胸", "Cable"),
    ("雙槓撐體", "胸", "自重"),
    ("伏地挺身", "胸", "自重"),
    # 背
    ("硬舉", "背", "槓鈴"),
    ("引體向上", "背", "自重"),
    ("滑輪下拉", "背", "Cable"),
    ("划船", "背", "槓鈴"),
    ("單手划船", "背", "啞鈴"),
    ("坐姿划船", "背", "Cable"),
    ("T 槓划船", "背", "器械"),
    ("聳肩", "背", "啞鈴"),
    # 腿
    ("深蹲", "腿", "槓鈴"),
    ("前蹲舉", "腿", "槓鈴"),
    ("腿推", "腿", "器械"),
    ("羅馬尼亞硬舉", "腿", "槓鈴"),
    ("腿屈伸", "腿", "器械"),
    ("腿後勾", "腿", "器械"),
    ("保加利亞分腿蹲", "腿", "啞鈴"),
    ("小腿舉踵", "腿", "器械"),
    # 肩
    ("肩推", "肩", "槓鈴"),
    ("肩推", "肩", "啞鈴"),
    ("側平舉", "肩", "啞鈴"),
    ("前平舉", "肩", "啞鈴"),
    ("反向飛鳥", "肩", "器械"),
    ("臉拉", "肩", "Cable"),
    # 手臂
    ("二頭彎舉", "手臂", "槓鈴"),
    ("二頭彎舉", "手臂", "啞鈴"),
    ("錘式彎舉", "手臂", "啞鈴"),
    ("三頭下壓", "手臂", "Cable"),
    ("三頭繩索下拉", "手臂", "Cable"),
    ("窄握臥推", "手臂", "槓鈴"),
    ("法式推舉", "手臂", "槓鈴"),
    # 核心
    ("腹肌捲腹", "核心", "自重"),
    ("平板支撐", "核心", "自重"),
    ("懸吊舉腿", "核心", "自重"),
]


def _seed_default_exercises() -> None:
    """把 DEFAULT_EXERCISES 裡缺少的動作塞進 DB；同名且已存在時只補 equipment。

    - 舊資料不會被覆蓋（category、notes 使用者可能已自訂）
    - 測試環境可設 GYM_SKIP_SEED=1 跳過，避免在測試 DB 之外產生副作用
    """
    import os
    if os.environ.get("GYM_SKIP_SEED"):
        return
    db = SessionLocal()
    try:
        # 以 (name, equipment) 當 key：同名但器材不同視為不同變體
        existing = {(e.name, e.equipment): e for e in db.query(models.Exercise).all()}
        changed = False
        for name, category, equipment in DEFAULT_EXERCISES:
            if (name, equipment) in existing:
                continue
            db.add(models.Exercise(name=name, category=category, equipment=equipment))
            changed = True
        if changed:
            db.commit()
    finally:
        db.close()


_seed_default_exercises()

app = FastAPI(
    title="Gym Tracker",
    description="個人健身記錄 API",
    version="0.1.0",
)

# ---------- Basic Auth ----------
# 部署用：設環境變數 GYM_USERNAME / GYM_PASSWORD 之後，整個站（含 API、首頁、靜態檔）
# 都會要求 HTTP Basic Auth。環境變數未設則完全不擋（給本地開發用）。
_AUTH_USER = os.environ.get("GYM_USERNAME", "").strip()
_AUTH_PASS = os.environ.get("GYM_PASSWORD", "").strip()


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """整站 HTTP Basic Auth。health check 保持公開方便 uptime 監測。"""
    async def dispatch(self, request: Request, call_next):
        if not _AUTH_USER or not _AUTH_PASS:
            return await call_next(request)
        # health check 免驗
        if request.url.path == "/api/health":
            return await call_next(request)

        header = request.headers.get("authorization", "")
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header[6:]).decode("utf-8")
                user, _, pwd = decoded.partition(":")
                # 用 compare_digest 避免 timing attack
                if (secrets.compare_digest(user, _AUTH_USER)
                        and secrets.compare_digest(pwd, _AUTH_PASS)):
                    return await call_next(request)
            except Exception:
                pass
        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Gym Tracker"'},
        )


app.add_middleware(BasicAuthMiddleware)

# CORS：開發階段預設開放，部署時用 ALLOWED_ORIGINS 環境變數限制
#   例：ALLOWED_ORIGINS="https://gym-tracker.example.com,https://foo.bar"
import os as _os
_allowed_origins_env = _os.environ.get("ALLOWED_ORIGINS", "").strip()
_allowed_origins = (
    [o.strip() for o in _allowed_origins_env.split(",") if o.strip()]
    if _allowed_origins_env else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 routers
app.include_router(exercises.router)
app.include_router(workouts.router)
app.include_router(routines.router)
app.include_router(data.router)
app.include_router(analytics.router)


# ========== 前端靜態檔案 ==========
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def index():
    """首頁直接回傳 index.html。"""
    return FileResponse(STATIC_DIR / "index.html")


# 其他靜態檔案（之後若有 css/js 檔）
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health", tags=["system"])
def health_check():
    return {"status": "ok"}
