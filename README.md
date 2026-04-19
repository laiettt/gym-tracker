# Gym Tracker

個人健身記錄工具。FastAPI + SQLAlchemy + SQLite + Alpine.js。

## 功能

- 記錄每次訓練的動作、組數、重量、次數、備註
- 動作按肌群篩選 / 可標註器材（槓鈴、啞鈴、Cable、器械…）
- 查看歷史訓練記錄，可展開看細節
- 單動作進步曲線圖（最大重量 / 總訓練量 / 推估 1RM）
- 個人最佳成績（PR）徽章
- 課表範本（API 已支援，前端待做）
- JSON 匯出 / 匯入

## 環境需求

- Python 3.12
- Windows / macOS / Linux

## 第一次啟動

### 1. 建立虛擬環境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

啟動後 terminal 前面會出現 `(venv)`。

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 啟動開發伺服器

```bash
uvicorn app.main:app --reload
```

看到這行就代表成功：

```
Uvicorn running on http://127.0.0.1:8000
```

### 4. 打開瀏覽器

- 前端首頁：<http://127.0.0.1:8000>
- API 文件（Swagger UI）：<http://127.0.0.1:8000/docs>
- 健康檢查：<http://127.0.0.1:8000/api/health>

## 建議的第一次使用流程

第一次啟動時會自動塞入一份常見動作清單（胸 / 背 / 腿 / 肩 / 手臂 / 核心），直接到「記錄」分頁開始使用即可。想加自己的動作到「動作庫」新增。

## 測試

```bash
pytest
```

測試走記憶體 SQLite、不會動到 `gym.db`；啟動時透過 `GYM_SKIP_SEED=1` 跳過 default seed。

## 資料庫

開發階段用 SQLite，資料存在專案根目錄的 `gym.db`。

- 用 PyCharm 的 Database 工具可以直接打開看內容
- 或用 [DB Browser for SQLite](https://sqlitebrowser.org)
- 備份就是把 `gym.db` 複製走，或用前端「匯出」功能產生 JSON

要換 PostgreSQL 或 MySQL，改 `app/database.py` 裡的 `SQLALCHEMY_DATABASE_URL` 就好。

## 專案結構

```
gym-tracker/
├── app/
│   ├── main.py              # FastAPI 入口（含啟動 seed / 輕量 migration）
│   ├── database.py          # DB 連線
│   ├── models.py            # SQLAlchemy 資料表
│   ├── schemas.py           # Pydantic 驗證 schemas
│   ├── routers/
│   │   ├── exercises.py     # /api/exercises（含 history、PR）
│   │   ├── workouts.py      # /api/workouts（含 set 重新排序）
│   │   ├── routines.py      # /api/routines
│   │   └── data.py          # /api/export、/api/import
│   └── static/
│       └── index.html       # 前端（單一檔案 + Alpine.js + Tailwind CDN）
├── tests/                    # pytest
├── alembic/                  # 資料庫 migration（之後用）
├── requirements.txt
├── .gitignore
└── README.md
```

## API 一覽

動作庫：

- `GET    /api/exercises`
- `POST   /api/exercises`
- `GET    /api/exercises/{id}`
- `PATCH  /api/exercises/{id}`
- `DELETE /api/exercises/{id}`
- `GET    /api/exercises/{id}/history`（單動作進步曲線資料）
- `GET    /api/exercises/{id}/prs`（個人最佳成績）

訓練記錄：

- `GET    /api/workouts`
- `POST   /api/workouts`
- `GET    /api/workouts/{id}`
- `PATCH  /api/workouts/{id}`
- `DELETE /api/workouts/{id}`
- `POST   /api/workouts/{id}/sets`
- `DELETE /api/workouts/{id}/sets/{set_id}`
- `POST   /api/workouts/{id}/sets/reorder`

課表範本：

- `GET    /api/routines`
- `POST   /api/routines`
- `GET    /api/routines/{id}`
- `DELETE /api/routines/{id}`

資料匯出 / 匯入：

- `GET    /api/export`
- `POST   /api/import`

完整 API 文件自動在 `/docs`。

## 之後要做的事（roadmap）

- [ ] 前端加上「從課表開始訓練」流程
- [ ] 部署到 Railway
- [ ] 換成 PostgreSQL
- [ ] 加上簡易登入（多裝置同步自用資料）
- [ ] 改用 Alembic 管 migration（目前用 `create_all` + 手動 ALTER 偷懶）

## 開發提示

- `--reload` 參數讓你改 code 自動重啟，不用手動
- 改 models 後 SQLite 不會自動同步，最簡單就是刪掉 `gym.db` 讓它重建（開發階段沒關係）；若已有正式資料，寫個一次性 `ALTER TABLE` 小函式在啟動時跑過一次
- 之後正式上線前要導入 Alembic 做 migration
