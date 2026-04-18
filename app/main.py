"""FastAPI application entry point."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models
from app.database import SessionLocal, engine
from app.routers import exercises, workouts, routines

# 建立資料表（開發階段用，正式環境會用 Alembic migration）
models.Base.metadata.create_all(bind=engine)


def _seed_default_exercises() -> None:
    """資料庫沒有任何動作時，塞入常見動作作為測試/起始資料。

    測試環境可設 GYM_SKIP_SEED=1 跳過，避免在測試 DB 之外產生副作用。
    """
    import os
    if os.environ.get("GYM_SKIP_SEED"):
        return
    db = SessionLocal()
    try:
        if db.query(models.Exercise).count() > 0:
            return
        defaults = [
            ("深蹲", "腿"),
            ("硬舉", "背"),
            ("臥推", "胸"),
            ("肩推", "肩"),
            ("引體向上", "背"),
            ("滑輪下拉", "背"),
            ("槓鈴划船", "背"),
            ("啞鈴臥推", "胸"),
            ("腿推", "腿"),
            ("羅馬尼亞硬舉", "腿"),
            ("二頭彎舉", "手臂"),
            ("三頭下壓", "手臂"),
            ("側平舉", "肩"),
            ("腹肌捲腹", "核心"),
        ]
        db.add_all([models.Exercise(name=n, category=c) for n, c in defaults])
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
