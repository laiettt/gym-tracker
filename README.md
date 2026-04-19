# Gym Tracker

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009485)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green)]()

輕量級個人健身訓練記錄與分析平台。以 Web 介面取代傳統試算表流程，支援手機與桌面瀏覽器，並提供自動化的訓練分析與漸進式負荷建議。

## 核心功能

### 訓練記錄
- 逐組記錄動作、重量、次數、RPE 與備註
- 動作庫依肌群篩選；同一動作可區分器材（槓鈴、啞鈴、Cable、器械…）
- 組間休息計時器
- 課表範本（API 已支援，前端待開發）

### 數據分析
- **單動作進步曲線**：最大重量 / 總訓練量 / 推估 1RM（Epley 公式）
- **個人最佳成績（PR）**：以歷史重量與推估 1RM 雙軌追蹤
- **結束訓練分析**：與上次同肌群訓練的總量比較，自動標示 PR、停滯、狀態偏低
- **月度分析**：訓練天數、組數、總量、肌群分布、常練動作排行、PR 統計，並根據推拉平衡、訓練頻率、動作集中度等產出下月調整建議

### 資料管理
- 歷史紀錄以列表或月曆檢視
- JSON 格式匯出 / 匯入（跨環境搬遷、備份）

## 技術架構

| 層級 | 技術 |
|---|---|
| 後端 | FastAPI, SQLAlchemy 2.x, Pydantic v2 |
| 資料庫 | SQLite（開發）/ PostgreSQL（部署） |
| 前端 | Alpine.js + Tailwind CSS（CDN，無 build step）、Chart.js |
| 測試 | pytest（記憶體 SQLite） |
| 部署 | Render（Web Service）+ Neon（Serverless Postgres） |

## 快速開始

### 需求
- Python 3.12+

### 安裝與啟動

```bash
# 建立虛擬環境
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 安裝套件
pip install -r requirements.txt

# 啟動開發伺服器
uvicorn app.main:app --reload
```

啟動後可用：
- 前端介面：<http://127.0.0.1:8000>
- API 文件（Swagger UI）：<http://127.0.0.1:8000/docs>

首次啟動會自動載入預設動作清單（胸、背、腿、肩、手臂、核心）。

### 測試

```bash
pytest
```

### 產生示範資料

用於測試結束訓練分析與月度分析：

```bash
python -m scripts.seed_demo
```

會建立跨月歷史訓練紀錄以及一筆進行中的當日訓練（含可觸發 PR、停滯、狀態偏低三種情境的組數）。

## 專案結構

```
gym-tracker/
├── app/
│   ├── main.py                # FastAPI 入口（啟動 seed、輕量 migration、Basic Auth middleware）
│   ├── database.py            # 資料庫連線（支援 DATABASE_URL 環境變數）
│   ├── models.py              # SQLAlchemy ORM
│   ├── schemas.py             # Pydantic schemas
│   ├── routers/
│   │   ├── exercises.py       # /api/exercises（含進步曲線、PR）
│   │   ├── workouts.py        # /api/workouts（含組數排序、結束訓練分析）
│   │   ├── routines.py        # /api/routines
│   │   ├── analytics.py       # /api/analytics（月度分析）
│   │   └── data.py            # /api/export、/api/import
│   └── static/
│       └── index.html         # 前端單檔應用
├── scripts/
│   └── seed_demo.py           # 示範資料腳本
├── tests/                     # pytest 測試套件
├── Procfile                   # Railway / Heroku 啟動設定
├── .env.example               # 環境變數範本
└── requirements.txt
```

完整 API 規格見啟動後的 `/docs`。

## 資料庫

開發階段預設使用 SQLite（`gym.db`）；設定 `DATABASE_URL` 環境變數可切換至 PostgreSQL 或其他 SQLAlchemy 支援的資料庫。

- 檢視本地 DB：JetBrains Database 工具 / [DB Browser for SQLite](https://sqlitebrowser.org)
- 備份：直接複製 `gym.db`，或透過前端「匯出」產出 JSON
- Schema 異動：目前採用 `create_all` 搭配啟動時輕量 migration（補欄位、重建索引、合併舊動作名稱）；正式導入 Alembic 列於 Roadmap

## 部署（Render + Neon）

採用免費組合：Render 提供 Web Service、Neon 提供 Serverless PostgreSQL，兩者皆有永久免費方案可承載單人自用流量。

### 1. 建立資料庫（Neon）

1. 於 [Neon](https://neon.tech) 註冊並建立 Project
2. Region 建議選 **AWS Asia Pacific 1 (Singapore)**（延遲較低）
3. 複製 **Connection string**（格式：`postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`）

### 2. 建立 Web Service（Render）

1. 於 [Render](https://render.com) 選擇 **New → Web Service**，連結 GitHub repo
2. 基本設定：

   | 欄位 | 值 |
   |---|---|
   | Region | Singapore |
   | Branch | `main` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | Free |

3. 環境變數：

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Neon connection string |
   | `GYM_USERNAME` | HTTP Basic Auth 帳號 |
   | `GYM_PASSWORD` | HTTP Basic Auth 密碼 |
   | `PYTHON_VERSION` | `3.12.7` |
   | `ALLOWED_ORIGINS` | 前端網域（可選，用於限制 CORS） |

4. 送出後 Render 會自動 build & deploy，後續每次 push 到 `main` 皆會觸發自動部署

### 3. 資料遷移

前端「匯出」下載 JSON → 於新環境前端「匯入」。

完整環境變數清單見 `.env.example`。

### Free Tier 注意事項

- **Render Free Web Service** 會在閒置 15 分鐘後休眠；下次請求會有約 30 秒冷啟動
- **Neon Free Tier** 提供 0.5 GB 儲存與 191.9 CU-小時/月，個人自用量通常遠低於上限

## 安全性

- HTTP Basic Auth：設定 `GYM_USERNAME` + `GYM_PASSWORD` 後整站受保護；`/api/health` 保留公開供 uptime 監測
- CORS：預設全開（本地開發），生產環境透過 `ALLOWED_ORIGINS` 白名單限制
- 秘密資訊一律經環境變數注入，專案 code 不含任何連線字串或憑證

## Roadmap

- [ ] 前端「從課表開始訓練」完整流程
- [ ] 多使用者帳號與資料隔離
- [ ] PWA（自訂 icon、離線支援）
- [ ] 導入 Alembic 管理 migration

## License

MIT
