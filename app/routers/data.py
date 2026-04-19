"""資料匯出 / 匯入 API。"""
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api", tags=["data"])


@router.get("/export", response_model=schemas.ExportData)
def export_data(db: Session = Depends(get_db)):
    """匯出全部資料（動作庫、訓練記錄、課表）為 JSON。"""
    exercises = db.query(models.Exercise).order_by(models.Exercise.name).all()
    workouts = db.query(models.Workout).order_by(models.Workout.date).all()
    routines = db.query(models.Routine).order_by(models.Routine.name).all()

    ex_name = {e.id: e.name for e in exercises}

    export_exercises = [
        schemas.ExerciseCreate(name=e.name, category=e.category, notes=e.notes)
        for e in exercises
    ]

    export_workouts = [
        schemas.ExportWorkout(
            date=w.date,
            notes=w.notes,
            duration_minutes=w.duration_minutes,
            sets=[
                schemas.ExportWorkoutSet(
                    exercise_name=ex_name.get(s.exercise_id, "未知"),
                    set_number=s.set_number,
                    weight=s.weight,
                    reps=s.reps,
                    rpe=s.rpe,
                    notes=s.notes,
                )
                for s in sorted(w.sets, key=lambda s: s.set_number)
            ],
        )
        for w in workouts
    ]

    export_routines = [
        schemas.ExportRoutine(
            name=r.name,
            description=r.description,
            exercises=[
                schemas.ExportRoutineExercise(
                    exercise_name=ex_name.get(re.exercise_id, "未知"),
                    order_index=re.order_index,
                    target_sets=re.target_sets,
                    target_reps=re.target_reps,
                )
                for re in r.routine_exercises
            ],
        )
        for r in routines
    ]

    return schemas.ExportData(
        exercises=export_exercises,
        workouts=export_workouts,
        routines=export_routines,
    )


@router.post("/import", response_model=Dict[str, Any])
def import_data(payload: schemas.ExportData, db: Session = Depends(get_db)):
    """匯入資料；動作名稱重複者跳過，訓練與課表一律新增。"""
    stats = {"exercises": 0, "workouts": 0, "routines": 0}

    # 1. 建立動作（重複跳過）
    for ex_data in payload.exercises:
        existing = db.query(models.Exercise).filter_by(name=ex_data.name).first()
        if not existing:
            db.add(models.Exercise(**ex_data.model_dump()))
            stats["exercises"] += 1
    db.flush()

    # 建立 exercise name -> id 對照表
    ex_id_map = {e.name: e.id for e in db.query(models.Exercise).all()}

    # 2. 建立訓練記錄
    for w_data in payload.workouts:
        workout = models.Workout(
            date=w_data.date,
            notes=w_data.notes,
            duration_minutes=w_data.duration_minutes,
        )
        db.add(workout)
        db.flush()
        for s_data in w_data.sets:
            ex_id = ex_id_map.get(s_data.exercise_name)
            if ex_id is None:
                continue  # 找不到對應動作就跳過這組
            db.add(models.WorkoutSet(
                workout_id=workout.id,
                exercise_id=ex_id,
                set_number=s_data.set_number,
                weight=s_data.weight,
                reps=s_data.reps,
                rpe=s_data.rpe,
                notes=s_data.notes,
            ))
        stats["workouts"] += 1

    # 3. 建立課表
    for r_data in payload.routines:
        routine = models.Routine(
            name=r_data.name,
            description=r_data.description,
        )
        db.add(routine)
        db.flush()
        for re_data in r_data.exercises:
            ex_id = ex_id_map.get(re_data.exercise_name)
            if ex_id is None:
                continue
            db.add(models.RoutineExercise(
                routine_id=routine.id,
                exercise_id=ex_id,
                order_index=re_data.order_index,
                target_sets=re_data.target_sets,
                target_reps=re_data.target_reps,
            ))
        stats["routines"] += 1

    db.commit()
    return {"imported": stats}
