# Gym Tracker

個人自用的健身記錄工具。用來取代 Excel 手打組數、重量、次數的流程；手機和電腦都能用，開瀏覽器就上。

## 功能

- 記錄每次訓練的動作、組數、重量、次數、RPE、備註
- 動作依肌群篩選，同一動作可區分器材（槓鈴 / 啞鈴 / Cable / 器械…）
- 歷史訓練：列表 + 月曆兩種檢視，月曆點日期可看當日記錄
- 單動作進步曲線（最大重量 / 總量 / 推估 1RM）、個人最佳成績（PR）徽章
- **結束訓練分析**：本次 vs 上次同肌群總量、PR / 停滯 / 狀態偏低提示
- **月度分析**：訓練天數、組數、總量、肌群分布、常練動作、PR、下月建議（肌群平衡、推拉比、頻率等）
- 組間休息計時器
- 課表範本（API 已支援，前端待做）
- JSON 匯出 / 匯入

## 技術棧

- 後端：FastAPI + SQLAlchemy + SQLite
- 前端：單一 HTML + Alpine.js + Tailwind（CDN，無 build step）
- 測試：pytest（記憶體 SQLite、不動到 `gym.db`）

## 啟動

```bash
# 1. 建虛擬環境
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 2. 安裝
pip install -r requirements.txt

# 3. 啟動
uvicorn app.main:app --reload
```

打開：
- 前端：<http://127.0.0.1:8000>
- Swagger：<http://127.0.0.1:8000/docs>

第一次啟動會自動塞一份常見動作清單（胸 / 背 / 腿 / 肩 / 手臂 / 核心）。

## 測試

```bash
pytest
```

## 產生假資料

想看月度分析 / 結束訓練分析的 Modal，跑：

```bash
python -m scripts.seed_demo
```

會建立上個月 + 本月共 12 筆歷史訓練，以及一筆進行中的今日訓練（含可觸發 PR / 停滯 / 偏低三種 badge 的組數）。

## 專案結構

```
gym-tracker/
├── app/
│   ├── main.py              # FastAPI 入口（seed + 輕量 migration）
│   ├── database.py          # DB 連線
│   ├── models.py            # SQLAlchemy 資料表
│   ├── schemas.py           # Pydantic 驗證
│   ├── routers/
│   │   ├── exercises.py     # /api/exercises（含 history、PR）
│   │   ├── workouts.py      # /api/workouts（含 reorder、分析）
│   │   ├── routines.py      # /api/routines
│   │   ├── analytics.py     # /api/analytics（月度分析）
│   │   └── data.py          # /api/export、/api/import
│   └── static/index.html    # 前端（單檔）
├── scripts/
│   └── seed_demo.py         # 一次性假資料腳本
├── tests/                   # pytest
└── requirements.txt
```

完整 API 見啟動後的 `/docs`。

## 資料庫

- 開發階段用 SQLite，資料存在 `gym.db`
- 想看內容：PyCharm Database 工具 或 [DB Browser for SQLite](https://sqlitebrowser.org)
- 備份：複製 `gym.db`，或用前端「匯出」產出 JSON
- 換 PostgreSQL / MySQL：改 `app/database.py` 裡的 `SQLALCHEMY_DATABASE_URL`

目前沒接 Alembic。改 model 後啟動會跑輕量 migration（補欄位、重建 index、重命名舊動作），需要清資料就刪掉 `gym.db` 讓它重建。

## 部署到 Railway

1. 在 Railway 建 project，從 GitHub 匯入這個 repo。
2. 在同一個 project 加一個 PostgreSQL plugin；Railway 會自動把 `DATABASE_URL` 注入到 web service。
3. 視需要在 Variables 加：
   - `ALLOWED_ORIGINS` = 你的前端網址（限制 CORS）
4. 部署。Railway 會吃 `Procfile` 啟動 `uvicorn`。

首次部署後在 Postgres 是空的，startup 會自動 `create_all` 建表、跑 seed。要把本地 SQLite 資料搬過去，用前端的「匯出」產 JSON，再到部署後的站點「匯入」。

環境變數清單見 `.env.example`。

## Roadmap

- [ ] 前端「從課表開始訓練」流程
- [ ] 簡易登入（多裝置同步）
- [ ] 導入 Alembic
