# Gym Tracker

個人健身記錄工具。FastAPI + SQLAlchemy + SQLite + Alpine.js。

## 功能

- 記錄每次訓練的動作、組數、重量、次數、RPE
- 查看歷史訓練記錄
- 管理動作庫
- 預設課表範本（API 已支援，前端待做）
- 單一動作的歷史進步資料（API 已支援，前端圖表待做）

## 環境需求

- Python 3.11+
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

1. 先打開首頁切到「動作庫」分頁
2. 新增幾個你常做的動作（例如：深蹲、臥推、硬舉、滑輪下拉）
3. 切回「記錄」分頁開始記錄

## 資料庫

開發階段用 SQLite，資料存在專案根目錄的 `gym.db`。

- 用 PyCharm 的 Database 工具可以直接打開看內容
- 或用 [DB Browser for SQLite](https://sqlitebrowser.org)
- 備份就是把 `gym.db` 複製走

要換 PostgreSQL 或 MySQL，改 `app/database.py` 裡的 `SQLALCHEMY_DATABASE_URL` 就好。

## 專案結構

```
gym-tracker/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── database.py          # DB 連線
│   ├── models.py            # SQLAlchemy 資料表
│   ├── schemas.py           # Pydantic 驗證 schemas
│   ├── routers/
│   │   ├── exercises.py     # /api/exercises
│   │   ├── workouts.py      # /api/workouts
│   │   └── routines.py      # /api/routines
│   └── static/
│       └── index.html       # 前端（單一檔案）
├── alembic/                 # 資料庫 migration（之後用）
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

訓練記錄：

- `GET    /api/workouts`
- `POST   /api/workouts`
- `GET    /api/workouts/{id}`
- `DELETE /api/workouts/{id}`
- `POST   /api/workouts/{id}/sets`
- `DELETE /api/workouts/{id}/sets/{set_id}`

課表範本：

- `GET    /api/routines`
- `POST   /api/routines`
- `GET    /api/routines/{id}`
- `DELETE /api/routines/{id}`

完整 API 文件自動在 `/docs`。

## 之後要做的事（roadmap）

- [ ] 前端加上「從課表開始訓練」流程
- [ ] 前端加上動作進步曲線圖（接 `/api/exercises/{id}/history`）
- [ ] 加上個人最佳成績（PR）追蹤
- [ ] 匯出 / 匯入資料
- [ ] 部署到 Railway
- [ ] 換成 PostgreSQL
- [ ] 加上簡易登入（多裝置同步自用資料）
- [ ] 改用 Alembic 管 migration（目前用 `create_all` 偷懶）

## 開發提示

- `--reload` 參數讓你改 code 自動重啟，不用手動
- 改 models 後 SQLite 不會自動同步，最簡單就是刪掉 `gym.db` 讓它重建（開發階段沒關係）
- 之後正式上線前要導入 Alembic 做 migration
