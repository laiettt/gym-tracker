# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案目的

個人自用的健身記錄工具。使用者原本用 Excel 記錄訓練（重量、次數、組數），要升級成雲端服務，手機和電腦都能用。

## 使用者背景與溝通風格

- Python 後端工程師，熟悉 SQL（MSSQL、MySQL），**不熟**前端框架（React/Vue/Next.js）與雲端平台（AWS/Vercel/Railway）。
- 開發環境：Windows 桌機 + PyCharm（先前用 Mac）。
- 使用繁體中文溝通；技術細節可以講得具體，但前端與雲端要多補脈絡。
- 循序漸進，一次一件事，明確告訴使用者「現在該做什麼」而不是列一堆選項。

## 指令

先啟動 venv（Windows: `venv\Scripts\activate`；macOS/Linux: `source venv/bin/activate`）。

- 安裝套件：`pip install -r requirements.txt`
- 啟動開發伺服器（自動 reload）：`uvicorn app.main:app --reload`
- Swagger UI：http://127.0.0.1:8000/docs
- Health check：http://127.0.0.1:8000/api/health

目前沒有設定測試、linter、formatter。

## 架構

FastAPI + SQLAlchemy + SQLite + Alpine.js 的單人健身紀錄。前端是單一靜態檔 `app/static/index.html` 掛在 `/`，其餘全部是 `/api/*` 下的 JSON API。

**Request flow：** `app/main.py` 掛三個 routers — `exercises`、`workouts`、`routines`，每個都透過 `app/database.py` 的 `Depends(get_db)` 取得 per-request SQLAlchemy session。Pydantic schemas 在 `app/schemas.py`，ORM models 在 `app/models.py`。

**資料模型（見 `app/models.py`）：**
- `Exercise` — 動作庫（深蹲、臥推…），`name` unique。
- `Routine` + `RoutineExercise` — 課表範本（PPL、上下肢分化…）。`RoutineExercise` 為 join table，有 `order_index`、`target_sets`、`target_reps`；從 `Routine` cascade delete。
- `Workout` — 一次訓練，可選擇性關聯到 `Routine`。
- `WorkoutSet`（table name `sets`）— 每一組實際紀錄（weight/reps/RPE），從 `Workout` cascade delete。**class 名稱叫 `WorkoutSet` 不是 `Set`，為了避免蓋到 Python 內建 `set`**；資料表名仍是 `sets`。

**Schema 管理：** 啟動時 `app/main.py` 跑 `models.Base.metadata.create_all(bind=engine)`。目前 **沒有** 真正接上 Alembic（`alembic/` 只是 placeholder — 沒有 `alembic.ini`，`versions/` 是空的）。開發期若改了 model，直接刪 `gym.db` 讓它重建。

**DB 切換點：** `app/database.py` 的 `SQLALCHEMY_DATABASE_URL`。要換 PostgreSQL/MySQL 時，連 SQLite 專用的 `connect_args={"check_same_thread": False}` 一起拿掉。

**CORS** 全開（`allow_origins=["*"]`），僅供本機開發，部署前要收緊。

## 技術選型與理由

| 層級 | 選擇 | 為什麼 |
|---|---|---|
| 後端框架 | FastAPI | 自動 API 文件，對 Python 後端最友善 |
| ORM | SQLAlchemy 2.x | Python 標配 |
| 資料驗證 | Pydantic v2 | 與 FastAPI 原生整合 |
| 開發 DB | SQLite | 零設定，`gym.db` 一個檔案 |
| 正式 DB（未來） | PostgreSQL | 雲端託管選項多 |
| 前端 | HTML + Alpine.js + Tailwind（CDN） | 使用者不熟前端框架，這組學習曲線最平緩 |
| Migration（未來） | Alembic | 開發階段先用 `create_all` 偷懶 |
| 部署（規劃） | Railway | 一鍵部署 FastAPI + PostgreSQL |

## 功能優先序 / 進度

已完成：
- 三組 CRUD API：`/api/exercises`、`/api/workouts`、`/api/routines`
- 單動作歷史資料 API：`GET /api/exercises/{id}/history`
- 前端基本介面（記錄 / 歷史 / 動作庫 三分頁）
- SQLite 自動建表

還沒做：
- [ ] 前端進步曲線圖表（接 `/api/exercises/{id}/history`，建議用 Chart.js）
- [ ] 前端「從課表開始訓練」流程
- [ ] 個人最佳成績（PR）追蹤
- [ ] 資料匯出/匯入（使用者原本的 Excel 資料需要匯入）
- [ ] 部署到 Railway
- [ ] 換 PostgreSQL
- [ ] 簡易登入（多裝置自用同步）
- [ ] 導入 Alembic 管理 migration

## 開發規範

- **檔案結構**：遵守現有 `app/routers/*.py` 一個 domain 一個檔案的模式。
- **資料驗證**：所有 request/response 一律走 Pydantic schema，不要直接回 ORM model。
- **SQL**：用 SQLAlchemy ORM，避免 raw SQL（特殊情境除外）。
- **前端**：維持 **單一** HTML 檔，用 Alpine.js + Tailwind CDN，**不要引入 build 工具**。
- **註解 / 文件**：重要設計決策用繁體中文註解說明；既有 docstring/comment 皆為繁中，編輯時維持同風格。

## 備註

- 使用者有 Claude Pro/Max 訂閱。
- 專案一開始在 Claude.ai 網頁版討論架構與技術選型，第一版骨架由網頁端 artifact 產出，之後轉到 Claude Code 繼續開發。
