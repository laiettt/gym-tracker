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

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依賴注入用的 DB session generator。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
