"""Analytics API - 跨越多次訓練的統計（月度總結等）。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.models import _utcnow_naive

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _month_range(year: int, month: int) -> tuple[datetime, datetime]:
    """回傳 [月初 00:00, 下月初 00:00)。"""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


@router.get("/monthly", response_model=schemas.MonthlyAnalytics)
def monthly_analytics(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    """月度訓練分析：天數、組數、總量、肌群佔比、常練動作、PR 次數。

    當月還沒結束時仍可呼叫，回傳 is_current_month=True 讓前端標示「本月進度」。
    """
    start, end = _month_range(year, month)
    now = _utcnow_naive()
    is_current = start <= now < end

    workouts = (
        db.query(models.Workout)
        .filter(models.Workout.date >= start, models.Workout.date < end)
        .all()
    )

    training_days: set[str] = set()
    total_sets = 0
    total_reps = 0
    total_volume = 0.0
    durations: list[int] = []
    # 肌群佔比
    group_sets: dict[str, int] = {}
    group_volume: dict[str, float] = {}
    # 動作累計
    ex_sets: dict[int, int] = {}
    ex_volume: dict[int, float] = {}
    ex_max_weight: dict[int, float] = {}
    ex_name: dict[int, str] = {}

    for w in workouts:
        training_days.add(w.date.strftime("%Y-%m-%d"))
        if w.duration_minutes:
            durations.append(w.duration_minutes)
        for s in w.sets:
            total_sets += 1
            if s.reps is not None:
                total_reps += s.reps
            vol = 0.0
            if s.weight is not None and s.reps is not None:
                vol = s.weight * s.reps
            total_volume += vol
            if s.exercise:
                ex_name[s.exercise_id] = s.exercise.name
                ex_sets[s.exercise_id] = ex_sets.get(s.exercise_id, 0) + 1
                ex_volume[s.exercise_id] = ex_volume.get(s.exercise_id, 0.0) + vol
                if s.weight is not None:
                    cur = ex_max_weight.get(s.exercise_id)
                    if cur is None or s.weight > cur:
                        ex_max_weight[s.exercise_id] = s.weight
                cat = s.exercise.category
                if cat:
                    group_sets[cat] = group_sets.get(cat, 0) + 1
                    group_volume[cat] = group_volume.get(cat, 0.0) + vol

    # 肌群佔比
    muscle_groups: list[schemas.MonthlyMuscleGroup] = []
    for cat, vol in group_volume.items():
        pct = round(vol / total_volume * 100, 1) if total_volume > 0 else 0.0
        muscle_groups.append(schemas.MonthlyMuscleGroup(
            category=cat, sets_count=group_sets.get(cat, 0), volume=vol, percentage=pct,
        ))
    muscle_groups.sort(key=lambda g: g.volume, reverse=True)

    # 常練動作 Top 5（依總量）
    top_ids = sorted(ex_volume.keys(), key=lambda i: ex_volume[i], reverse=True)[:5]
    top_exercises = [
        schemas.MonthlyTopExercise(
            exercise_id=i,
            exercise_name=ex_name[i],
            sets_count=ex_sets[i],
            total_volume=round(ex_volume[i], 1),
            max_weight=ex_max_weight.get(i),
        )
        for i in top_ids
    ]

    # PR 計算：該月內每個動作的最大重量 > 該月以前的歷史最大重量
    pr_names: list[str] = []
    for ex_id, month_max in ex_max_weight.items():
        prior_max = (
            db.query(models.WorkoutSet.weight)
            .join(models.Workout)
            .filter(
                models.WorkoutSet.exercise_id == ex_id,
                models.Workout.date < start,
                models.WorkoutSet.weight.isnot(None),
            )
            .order_by(models.WorkoutSet.weight.desc())
            .first()
        )
        prior_val = prior_max[0] if prior_max else None
        if prior_val is None or month_max > prior_val:
            pr_names.append(ex_name[ex_id])

    # 上月總量比較
    prev_start, prev_end = _month_range(year - 1, 12) if month == 1 else _month_range(year, month - 1)
    prev_workouts = (
        db.query(models.Workout)
        .filter(models.Workout.date >= prev_start, models.Workout.date < prev_end)
        .all()
    )
    prev_volume = sum(
        (s.weight * s.reps)
        for w in prev_workouts
        for s in w.sets
        if s.weight is not None and s.reps is not None
    )
    volume_delta_pct = None
    if prev_volume > 0:
        volume_delta_pct = round((total_volume - prev_volume) / prev_volume * 100, 1)

    avg_duration = round(sum(durations) / len(durations), 1) if durations else None

    suggestions = _build_suggestions(
        is_current=is_current,
        training_days=len(training_days),
        total_sets=total_sets,
        total_volume=total_volume,
        group_volume=group_volume,
        ex_sets=ex_sets,
        pr_names=pr_names,
        volume_delta_pct=volume_delta_pct,
    )

    return schemas.MonthlyAnalytics(
        year=year,
        month=month,
        is_current_month=is_current,
        training_days=len(training_days),
        total_workouts=len(workouts),
        total_sets=total_sets,
        total_reps=total_reps,
        total_volume=round(total_volume, 1),
        avg_duration_minutes=avg_duration,
        muscle_groups=muscle_groups,
        top_exercises=top_exercises,
        pr_count=len(pr_names),
        pr_exercise_names=pr_names,
        prev_month_total_volume=round(prev_volume, 1) if prev_volume else None,
        volume_delta_pct=volume_delta_pct,
        suggestions=suggestions,
    )


#: 主要肌群：推拉腿核心平衡的基本骨架，判斷比例用。
_MAIN_GROUPS = {"胸", "背", "腿", "肩"}


def _build_suggestions(
    *,
    is_current: bool,
    training_days: int,
    total_sets: int,
    total_volume: float,
    group_volume: dict[str, float],
    ex_sets: dict[int, int],
    pr_names: list[str],
    volume_delta_pct: float | None,
) -> list[str]:
    """根據月度資料生出「下月可以怎麼調整」的建議。

    規則都很保守，只挑明顯失衡的情況才發聲，避免建議太多顯得雜訊。
    當月還沒結束時只發正向鼓勵與肌群失衡提示，不做月度成長的結論。
    """
    tips: list[str] = []

    # 1. 訓練頻率
    if not is_current:
        if training_days < 8:
            tips.append(
                f"本月僅訓練 {training_days} 天，建議下個月維持至少每週 2~3 次（8~12 天）以累積適應。"
            )
        elif training_days >= 16:
            tips.append(
                f"本月訓練 {training_days} 天，頻率高，下個月可留意恢復，避免累積疲勞導致表現下滑。"
            )

    # 2. 肌群平衡：主要肌群佔比
    if total_volume > 0:
        main_pcts = {g: group_volume.get(g, 0) / total_volume * 100 for g in _MAIN_GROUPS}
        weak = [g for g, pct in main_pcts.items() if pct < 10 and group_volume.get(g, 0) < total_volume * 0.1]
        # 完全沒練到的主要肌群
        missing = [g for g in _MAIN_GROUPS if group_volume.get(g, 0) == 0]
        if missing:
            tips.append(
                f"本月完全沒練到 {'、'.join(missing)}，下個月建議至少安排 1~2 次相關動作。"
            )
        elif weak:
            weak_desc = "、".join(f"{g}({round(main_pcts[g], 1)}%)" for g in weak)
            tips.append(
                f"{weak_desc} 訓練量偏低，下個月可以補強這些部位到 15% 以上。"
            )

        # 推拉平衡：胸 vs 背
        chest = group_volume.get("胸", 0)
        back = group_volume.get("背", 0)
        if chest > 0 and back > 0:
            ratio = chest / back if back > 0 else float("inf")
            if ratio >= 1.8:
                tips.append(
                    f"胸的訓練量約是背的 {round(ratio, 1)} 倍，下個月建議補背（划船、引體向上）平衡體態。"
                )
            elif ratio <= 0.55:
                tips.append(
                    f"背的訓練量約是胸的 {round(1 / ratio, 1)} 倍，下個月可以多補胸推動作。"
                )

    # 3. 動作集中度：Top 1 動作組數佔比過高
    if ex_sets and total_sets > 0:
        top_sets = max(ex_sets.values())
        if top_sets / total_sets >= 0.4:
            tips.append(
                f"單一動作佔了 {round(top_sets / total_sets * 100)}% 的組數，下個月可以豐富動作變化，讓肌群刺激更全面。"
            )

    # 4. vs 上月總量
    if not is_current and volume_delta_pct is not None:
        if volume_delta_pct <= -15:
            tips.append(
                f"總訓練量比上月下降 {abs(volume_delta_pct)}%，下個月建議檢視是否因出席、受傷或強度下降，必要時回補一週基礎量。"
            )
        elif volume_delta_pct >= 25:
            tips.append(
                f"總訓練量比上月成長 {volume_delta_pct}%，表現不錯；下個月可以維持此量再提重量，而不是繼續堆組數。"
            )

    # 5. PR 肯定
    if not is_current and pr_names:
        tips.append(
            f"本月在 {'、'.join(pr_names[:3])}{'等動作' if len(pr_names) > 3 else ''} 有 PR，下個月保留這幾個主動作為重點，其他輔助動作用較輕重量維持。"
        )

    return tips
