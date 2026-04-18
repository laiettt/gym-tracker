"""Pydantic schemas for request/response validation.

分成三層：
- XxxBase:   共用欄位
- XxxCreate: 建立時需要的欄位
- Xxx:       回傳給 client 的完整欄位（含 id、created_at 等）
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict


# ========== Exercise ==========
class ExerciseBase(BaseModel):
    name: str
    category: Optional[str] = None
    notes: Optional[str] = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class Exercise(ExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ========== Set ==========
class WorkoutSetBase(BaseModel):
    exercise_id: int
    set_number: int
    weight: Optional[float] = None
    reps: Optional[int] = None  # 留空表示力竭
    rpe: Optional[float] = None
    notes: Optional[str] = None


class WorkoutSetCreate(WorkoutSetBase):
    pass


class WorkoutSet(WorkoutSetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workout_id: int


# ========== Workout ==========
class WorkoutBase(BaseModel):
    date: Optional[datetime] = None
    routine_id: Optional[int] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None


class WorkoutCreate(WorkoutBase):
    sets: List[WorkoutSetCreate] = []


class WorkoutUpdate(BaseModel):
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None
    routine_id: Optional[int] = None


class Workout(WorkoutBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: datetime
    sets: List[WorkoutSet] = []


# ========== Routine ==========
class RoutineExerciseBase(BaseModel):
    exercise_id: int
    order_index: int = 0
    target_sets: Optional[int] = None
    target_reps: Optional[int] = None


class RoutineExerciseCreate(RoutineExerciseBase):
    pass


class RoutineExercise(RoutineExerciseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    routine_id: int
    exercise: Optional[Exercise] = None


class RoutineBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoutineCreate(RoutineBase):
    exercises: List[RoutineExerciseCreate] = []


class Routine(RoutineBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    routine_exercises: List[RoutineExercise] = []


# ========== Analytics ==========
class ExerciseHistoryPoint(BaseModel):
    """單一動作的歷史資料點，用於畫進步曲線。"""
    date: datetime
    max_weight: Optional[float] = None
    total_volume: float  # sum(weight * reps)
    total_reps: int
    sets_count: int
