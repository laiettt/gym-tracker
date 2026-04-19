"""FastAPI application entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models
from app.database import SessionLocal, engine
from app.routers import exercises, workouts, routines, data

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


_ensure_exercise_equipment_column()


#: 常見健身動作的預設清單：(name, category, equipment)。
#: 新增動作時若同名已存在只會補 equipment，不會覆蓋使用者自訂的分類。
DEFAULT_EXERCISES: list[tuple[str, str, str | None]] = [
    # 胸
    ("槓鈴臥推", "胸", "槓鈴"),
    ("上斜槓鈴臥推", "胸", "槓鈴"),
    ("啞鈴臥推", "胸", "啞鈴"),
    ("上斜啞鈴臥推", "胸", "啞鈴"),
    ("蝴蝶機夾胸", "胸", "器械"),
    ("Cable 夾胸", "胸", "Cable"),
    ("雙槓撐體", "胸", "自重"),
    ("伏地挺身", "胸", "自重"),
    # 背
    ("硬舉", "背", "槓鈴"),
    ("引體向上", "背", "自重"),
    ("滑輪下拉", "背", "Cable"),
    ("槓鈴划船", "背", "槓鈴"),
    ("啞鈴單手划船", "背", "啞鈴"),
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
    ("啞鈴肩推", "肩", "啞鈴"),
    ("側平舉", "肩", "啞鈴"),
    ("前平舉", "肩", "啞鈴"),
    ("反向飛鳥", "肩", "器械"),
    ("臉拉", "肩", "Cable"),
    # 手臂
    ("槓鈴彎舉", "手臂", "槓鈴"),
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
    # 舊版已存在但沒有 equipment（保留名稱不動，留空待使用者自己填）
    ("臥推", "胸", None),
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
        existing = {e.name: e for e in db.query(models.Exercise).all()}
        changed = False
        for name, category, equipment in DEFAULT_EXERCISES:
            ex = existing.get(name)
            if ex is None:
                db.add(models.Exercise(name=name, category=category, equipment=equipment))
                changed = True
            elif equipment and not ex.equipment:
                ex.equipment = equipment
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

# 開發階段開放 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 routers
app.include_router(exercises.router)
app.include_router(workouts.router)
app.include_router(routines.router)
app.include_router(data.router)


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
