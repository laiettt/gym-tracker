"""Workouts API - 訓練記錄的 CRUD。"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.models import _utcnow_naive

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


@router.get("", response_model=List[schemas.Workout])
def list_workouts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """列出訓練記錄，依日期由新到舊。"""
    return (
        db.query(models.Workout)
        .order_by(models.Workout.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.post("", response_model=schemas.Workout, status_code=status.HTTP_201_CREATED)
def create_workout(payload: schemas.WorkoutCreate, db: Session = Depends(get_db)):
    """建立一次訓練記錄，可同時帶入 sets。"""
    workout_data = payload.model_dump(exclude={"sets"})
    if workout_data.get("date") is None:
        workout_data["date"] = _utcnow_naive()

    workout = models.Workout(**workout_data)
    db.add(workout)
    db.flush()  # 先拿到 workout.id

    for set_data in payload.sets:
        workout_set = models.WorkoutSet(
            workout_id=workout.id,
            **set_data.model_dump(),
        )
        db.add(workout_set)

    db.commit()
    db.refresh(workout)
    return workout


@router.get("/{workout_id}", response_model=schemas.Workout)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@router.patch("/{workout_id}", response_model=schemas.Workout)
def update_workout(
    workout_id: int,
    payload: schemas.WorkoutUpdate,
    db: Session = Depends(get_db),
):
    """更新 workout（目前用來存訓練時長 duration_minutes / 備註）。"""
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workout, field, value)
    db.commit()
    db.refresh(workout)
    return workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    db.delete(workout)
    db.commit()


# ========== Sets (巢狀在 workout 底下) ==========
@router.post(
    "/{workout_id}/sets",
    response_model=schemas.WorkoutSet,
    status_code=status.HTTP_201_CREATED,
)
def add_set_to_workout(
    workout_id: int,
    payload: schemas.WorkoutSetCreate,
    db: Session = Depends(get_db),
):
    """在既有的 workout 加一組記錄。"""
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    workout_set = models.WorkoutSet(workout_id=workout_id, **payload.model_dump())
    db.add(workout_set)
    db.commit()
    db.refresh(workout_set)
    return workout_set


@router.post("/{workout_id}/sets/reorder", response_model=schemas.Workout)
def reorder_sets(
    workout_id: int,
    payload: schemas.ReorderSetsRequest,
    db: Session = Depends(get_db),
):
    """依 payload.set_ids 的順序重設 set_number（從 1 開始）。"""
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    existing = {s.id: s for s in workout.sets}
    if set(existing.keys()) != set(payload.set_ids):
        raise HTTPException(status_code=400, detail="set_ids 必須涵蓋此 workout 所有 set")
    for i, sid in enumerate(payload.set_ids, start=1):
        existing[sid].set_number = i
    db.commit()
    db.refresh(workout)
    return workout


@router.get("/{workout_id}/analysis", response_model=schemas.WorkoutAnalysis)
def analyze_workout(workout_id: int, db: Session = Depends(get_db)):
    """分析一次訓練：總量、與上次同肌群比較、各動作 PR / 停滯 / 狀態偏低。

    偵測門檻：
    - 停滯：本次以前最近 3 次同動作的最大重量都等於今日 → 建議 +2.5kg
    - 狀態偏低：今日最大重量 < 最近 3 次的最高值
    - PR：今日最大重量超過歷史最大
    """
    workout = db.get(models.Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    total_volume = 0.0
    total_sets = len(workout.sets)
    total_reps = 0
    muscle_groups: set[str] = set()
    by_exercise: dict[int, list] = {}
    for s in workout.sets:
        if s.exercise and s.exercise.category:
            muscle_groups.add(s.exercise.category)
        if s.weight is not None and s.reps is not None:
            total_volume += s.weight * s.reps
        if s.reps is not None:
            total_reps += s.reps
        by_exercise.setdefault(s.exercise_id, []).append(s)

    # 上次同肌群 workout
    prev_same_group_volume = None
    volume_delta_pct = None
    if muscle_groups:
        other_workouts = (
            db.query(models.Workout)
            .filter(models.Workout.id != workout_id, models.Workout.date < workout.date)
            .order_by(models.Workout.date.desc())
            .all()
        )
        for w in other_workouts:
            w_groups = {s.exercise.category for s in w.sets if s.exercise and s.exercise.category}
            if w_groups & muscle_groups:
                vol = sum(
                    (s.weight * s.reps)
                    for s in w.sets
                    if s.weight is not None and s.reps is not None
                )
                prev_same_group_volume = vol
                if vol > 0:
                    volume_delta_pct = round((total_volume - vol) / vol * 100, 1)
                break

    exercises_analysis: list[schemas.ExerciseAnalysis] = []
    for ex_id, today_sets in by_exercise.items():
        exercise = db.get(models.Exercise, ex_id)
        if not exercise:
            continue
        valid_today = [s for s in today_sets if s.weight is not None]
        today_max = max((s.weight for s in valid_today), default=None)
        today_max_set = (
            next((s for s in valid_today if s.weight == today_max), None)
            if today_max is not None else None
        )

        prior_sets = (
            db.query(models.WorkoutSet)
            .join(models.Workout)
            .filter(
                models.WorkoutSet.exercise_id == ex_id,
                models.WorkoutSet.workout_id != workout_id,
                models.Workout.date < workout.date,
                models.WorkoutSet.weight.isnot(None),
            )
            .order_by(models.Workout.date)
            .all()
        )
        prior_by_wid: dict[int, dict] = {}
        for s in prior_sets:
            bucket = prior_by_wid.setdefault(s.workout_id, {"date": s.workout.date, "max": s.weight})
            if s.weight > bucket["max"]:
                bucket["max"] = s.weight
        prior_sessions = sorted(prior_by_wid.values(), key=lambda x: x["date"])
        prior_maxes = [x["max"] for x in prior_sessions]
        previous_max = max(prior_maxes, default=None)

        is_pr = today_max is not None and (previous_max is None or today_max > previous_max)
        is_stagnant = False
        is_below_recent = False
        suggestion: Optional[str] = None

        last3 = prior_maxes[-3:] if len(prior_maxes) >= 3 else []
        if is_pr:
            suggestion = f"🏆 PR 突破！超越過往最高 {previous_max or 0}kg"
        elif today_max is not None and len(last3) >= 3:
            if all(m == today_max for m in last3):
                is_stagnant = True
                suggestion = f"此重量已連續 {len(last3) + 1} 次，建議嘗試 +2.5kg"
            elif today_max < max(last3):
                is_below_recent = True
                suggestion = f"今日最大 {today_max}kg，低於近期最高 {max(last3)}kg，注意休息"

        exercises_analysis.append(schemas.ExerciseAnalysis(
            exercise_id=ex_id,
            exercise_name=exercise.name,
            today_max_weight=today_max,
            today_max_weight_reps=today_max_set.reps if today_max_set else None,
            previous_max_weight=previous_max,
            is_pr=is_pr,
            is_stagnant=is_stagnant,
            is_below_recent=is_below_recent,
            suggestion=suggestion,
        ))

    return schemas.WorkoutAnalysis(
        workout_id=workout.id,
        date=workout.date,
        total_volume=total_volume,
        total_sets=total_sets,
        total_reps=total_reps,
        muscle_groups=sorted(muscle_groups),
        previous_same_group_volume=prev_same_group_volume,
        volume_delta_pct=volume_delta_pct,
        exercises=exercises_analysis,
    )


@router.delete("/{workout_id}/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_set(workout_id: int, set_id: int, db: Session = Depends(get_db)):
    workout_set = (
        db.query(models.WorkoutSet)
        .filter_by(id=set_id, workout_id=workout_id)
        .first()
    )
    if not workout_set:
        raise HTTPException(status_code=404, detail="Set not found")
    db.delete(workout_set)
    db.commit()
