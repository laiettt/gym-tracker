"""Exercises API - 動作庫的 CRUD。"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


@router.get("", response_model=List[schemas.Exercise])
def list_exercises(db: Session = Depends(get_db)):
    """列出所有動作。"""
    return db.query(models.Exercise).order_by(models.Exercise.name).all()


@router.post("", response_model=schemas.Exercise, status_code=status.HTTP_201_CREATED)
def create_exercise(payload: schemas.ExerciseCreate, db: Session = Depends(get_db)):
    """新增一個動作。"""
    existing = db.query(models.Exercise).filter_by(name=payload.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Exercise '{payload.name}' already exists",
        )
    exercise = models.Exercise(**payload.model_dump())
    db.add(exercise)
    db.commit()
    db.refresh(exercise)
    return exercise


@router.get("/{exercise_id}", response_model=schemas.Exercise)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).get(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@router.patch("/{exercise_id}", response_model=schemas.Exercise)
def update_exercise(
    exercise_id: int,
    payload: schemas.ExerciseUpdate,
    db: Session = Depends(get_db),
):
    exercise = db.query(models.Exercise).get(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(exercise, key, value)

    db.commit()
    db.refresh(exercise)
    return exercise


@router.delete("/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    exercise = db.query(models.Exercise).get(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    db.delete(exercise)
    db.commit()


@router.get("/{exercise_id}/history", response_model=List[schemas.ExerciseHistoryPoint])
def get_exercise_history(exercise_id: int, db: Session = Depends(get_db)):
    """取得單一動作的歷史記錄，用於畫進步曲線。

    以每次訓練（workout）為單位聚合：max_weight、total_volume、total_reps。
    """
    exercise = db.query(models.Exercise).get(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # 抓這個動作的所有 sets，連 workout 一起 join
    sets = (
        db.query(models.WorkoutSet)
        .join(models.Workout)
        .filter(models.WorkoutSet.exercise_id == exercise_id)
        .order_by(models.Workout.date)
        .all()
    )

    # 以 workout_id 分組聚合
    grouped: dict[int, dict] = {}
    for s in sets:
        key = s.workout_id
        if key not in grouped:
            grouped[key] = {
                "date": s.workout.date,
                "max_weight": s.weight,
                "max_weight_reps": s.reps,
                "total_volume": 0.0,
                "total_reps": 0,
                "sets_count": 0,
            }
        g = grouped[key]
        if s.weight is not None:
            if g["max_weight"] is None or s.weight > g["max_weight"]:
                g["max_weight"] = s.weight
                g["max_weight_reps"] = s.reps
            if s.reps is not None:
                g["total_volume"] += s.weight * s.reps
        if s.reps is not None:
            g["total_reps"] += s.reps
        g["sets_count"] += 1

    return [
        schemas.ExerciseHistoryPoint(**v)
        for v in sorted(grouped.values(), key=lambda x: x["date"])
    ]


@router.get("/{exercise_id}/prs", response_model=schemas.ExercisePR)
def get_exercise_prs(exercise_id: int, db: Session = Depends(get_db)):
    """取得單一動作的個人最佳成績（PR）。

    回傳最大重量那組、以及 Epley 推估 1RM 最高那組。
    """
    exercise = db.query(models.Exercise).get(exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # 只計算 weight 和 reps 都有值的 sets
    sets = (
        db.query(models.WorkoutSet)
        .join(models.Workout)
        .filter(
            models.WorkoutSet.exercise_id == exercise_id,
            models.WorkoutSet.weight.isnot(None),
            models.WorkoutSet.reps.isnot(None),
            models.WorkoutSet.reps > 0,
        )
        .all()
    )

    if not sets:
        return schemas.ExercisePR(
            exercise_id=exercise_id,
            exercise_name=exercise.name,
        )

    def epley(weight, reps) -> float:
        return round(weight * (1 + reps / 30), 1)

    def to_entry(s) -> schemas.ExercisePREntry:
        return schemas.ExercisePREntry(
            date=s.workout.date,
            weight=s.weight,
            reps=s.reps,
            estimated_1rm=epley(s.weight, s.reps),
        )

    best_weight_set = max(sets, key=lambda s: s.weight)
    best_1rm_set = max(sets, key=lambda s: epley(s.weight, s.reps))

    return schemas.ExercisePR(
        exercise_id=exercise_id,
        exercise_name=exercise.name,
        best_weight=to_entry(best_weight_set),
        best_1rm=to_entry(best_1rm_set),
    )
