"""Database connection setup.

開發階段用 SQLite（專案根目錄的 gym.db 檔案）。
未來要換 PostgreSQL / MySQL 只要改 SQLALCHEMY_DATABASE_URL 即可。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./gym.db"

# SQLite 專用設定：允許多執行緒存取
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
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
