"""Database connection setup.

預設用 SQLite（本地開發），設定環境變數 DATABASE_URL 就會改用該 URL
（例：Railway 部署時會注入 Postgres URL）。
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _resolve_database_url() -> str:
    """讀取 DATABASE_URL，沒有就 fallback 到本地 SQLite。

    Railway / Heroku 舊版會塞 "postgres://..."，SQLAlchemy 2.x 只認
    "postgresql://"，這裡統一轉換避免啟動失敗。
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return "sqlite:///./gym.db"
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


SQLALCHEMY_DATABASE_URL = _resolve_database_url()

# SQLite 需要 check_same_thread=False 才能跨 thread；Postgres 不需要也不接受這個參數
_connect_args: dict = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

# pool_pre_ping：借連線前先 ping，避免拿到 Neon 砍掉的閒置連線（症狀是訓練
# 中途隔幾分鐘按下一組會跳 Request failed，重按一次又通）。
# pool_recycle=300：連線超過 5 分鐘強制回收，搭配 pre_ping 雙保險。
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依賴注入用的 DB session generator。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
