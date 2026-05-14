"""一次性修補：把所有 (workout, exercise) 內的 set_number 重新編成連續 1..N。

用途：早期版本前端用 length+1 計算 set_number，且刪除時不重編，導致歷史資料
出現跳號（1, 2, 4）或重號（2, 2, 3）。這支腳本掃過全表，依現有 set_number,
id 排序後重編，weight/reps/notes/rpe 一律不動。

使用步驟：
1. 從 Neon dashboard 複製 direct connection 字串。
2. 在終端機設環境變數（只在本視窗有效）：
       Windows cmd:    set DATABASE_URL=postgresql://...
       PowerShell:     $env:DATABASE_URL = "postgresql://..."
       bash/macOS:     export DATABASE_URL=postgresql://...
3. 先 dry-run 看會改什麼：
       python scripts/renumber_sets.py
4. 確認沒問題後加 --commit 真的寫入：
       python scripts/renumber_sets.py --commit

跑完後可以把這個檔案刪掉，或留著當紀念。
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict

# 讓 `python scripts/renumber_sets.py` 直接從專案根目錄跑也能 import app.*
sys.path.insert(0, ".")

from app.database import SessionLocal, SQLALCHEMY_DATABASE_URL  # noqa: E402
from app import models  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="真的寫入資料庫；不加這個參數則為 dry-run，只印出會改的內容。",
    )
    args = parser.parse_args()

    # 把連線字串裡的密碼遮掉，避免不小心截圖外洩
    safe_url = SQLALCHEMY_DATABASE_URL
    if "@" in safe_url and "://" in safe_url:
        scheme, rest = safe_url.split("://", 1)
        creds, host = rest.split("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            safe_url = f"{scheme}://{user}:***@{host}"
    print(f"連線目標：{safe_url}")
    print(f"模式：{'COMMIT（真的寫入）' if args.commit else 'DRY-RUN（只印不寫）'}")
    print("-" * 60)

    db = SessionLocal()
    try:
        sets = (
            db.query(models.WorkoutSet)
            .order_by(
                models.WorkoutSet.workout_id,
                models.WorkoutSet.exercise_id,
                models.WorkoutSet.set_number,
                models.WorkoutSet.id,
            )
            .all()
        )

        # 依 (workout_id, exercise_id) 分組
        groups: dict[tuple[int, int], list[models.WorkoutSet]] = defaultdict(list)
        for s in sets:
            groups[(s.workout_id, s.exercise_id)].append(s)

        changed = 0
        affected_groups = 0
        for (wid, eid), group in groups.items():
            group_changed = False
            for i, s in enumerate(group, start=1):
                if s.set_number != i:
                    print(
                        f"  workout={wid} exercise={eid} set_id={s.id}: "
                        f"{s.set_number} -> {i}"
                    )
                    s.set_number = i
                    changed += 1
                    group_changed = True
            if group_changed:
                affected_groups += 1

        print("-" * 60)
        print(f"掃描 {len(sets)} 筆 set，跨 {len(groups)} 個 (workout, exercise) 組合。")
        print(f"需要修正 {changed} 筆，涉及 {affected_groups} 個組合。")

        if changed == 0:
            print("資料已經乾淨，無事可做")
            return 0

        if args.commit:
            db.commit()
            print("已 commit")
        else:
            db.rollback()
            print("Dry-run 結束，未寫入。確認沒問題後加 --commit 再跑一次。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
