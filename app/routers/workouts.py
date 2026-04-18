"""Workouts API - 訓練記錄的 CRUD。"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

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
        workout_data["date"] = datetime.utcnow()

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
    workout = db.query(models.Workout).get(workout_id)
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
    workout = db.query(models.Workout).get(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(workout, field, value)
    db.commit()
    db.refresh(workout)
    return workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(models.Workout).get(workout_id)
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
    workout = db.query(models.Workout).get(workout_id)
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
    payload: dict,
    db: Session = Depends(get_db),
):
    """依 payload['set_ids'] 的順序重設 set_number（從 1 開始）。"""
    set_ids = payload.get("set_ids", [])
    workout = db.query(models.Workout).get(workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    existing = {s.id: s for s in workout.sets}
    if set(existing.keys()) != set(set_ids):
        raise HTTPException(status_code=400, detail="set_ids 必須涵蓋此 workout 所有 set")
    for i, sid in enumerate(set_ids, start=1):
        existing[sid].set_number = i
    db.commit()
    db.refresh(workout)
    return workout


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
