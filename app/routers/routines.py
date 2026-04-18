"""Routines API - 課表範本。"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/routines", tags=["routines"])


@router.get("", response_model=List[schemas.Routine])
def list_routines(db: Session = Depends(get_db)):
    return db.query(models.Routine).order_by(models.Routine.name).all()


@router.post("", response_model=schemas.Routine, status_code=status.HTTP_201_CREATED)
def create_routine(payload: schemas.RoutineCreate, db: Session = Depends(get_db)):
    routine = models.Routine(
        name=payload.name,
        description=payload.description,
    )
    db.add(routine)
    db.flush()

    for re_data in payload.exercises:
        re = models.RoutineExercise(
            routine_id=routine.id,
            **re_data.model_dump(),
        )
        db.add(re)

    db.commit()
    db.refresh(routine)
    return routine


@router.get("/{routine_id}", response_model=schemas.Routine)
def get_routine(routine_id: int, db: Session = Depends(get_db)):
    routine = db.query(models.Routine).get(routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    return routine


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_routine(routine_id: int, db: Session = Depends(get_db)):
    routine = db.query(models.Routine).get(routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail="Routine not found")
    db.delete(routine)
    db.commit()
