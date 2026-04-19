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
    equipment: Optional[str] = None
    notes: Optional[str] = None


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    equipment: Optional[str] = None
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
    max_weight_reps: Optional[int] = None  # 最大重量那組的次數，用於推估 1RM
    total_volume: float  # sum(weight * reps)
    total_reps: int
    sets_count: int


# ========== PR（個人最佳成績）==========
class ExercisePREntry(BaseModel):
    """單筆 PR 記錄。"""
    date: datetime
    weight: Optional[float]
    reps: Optional[int]
    estimated_1rm: Optional[float]  # Epley: weight * (1 + reps/30)


class ExercisePR(BaseModel):
    """動作的個人最佳成績。"""
    exercise_id: int
    exercise_name: str
    best_weight: Optional[ExercisePREntry] = None  # 最大重量的那組
    best_1rm: Optional[ExercisePREntry] = None      # 推估 1RM 最高的那組


# ========== 資料匯出 / 匯入 ==========
class ExportWorkoutSet(BaseModel):
    exercise_name: str
    set_number: int
    weight: Optional[float] = None
    reps: Optional[int] = None
    rpe: Optional[float] = None
    notes: Optional[str] = None


class ExportWorkout(BaseModel):
    date: Optional[datetime] = None
    notes: Optional[str] = None
    duration_minutes: Optional[int] = None
    sets: List[ExportWorkoutSet] = []


class ExportRoutineExercise(BaseModel):
    exercise_name: str
    order_index: int = 0
    target_sets: Optional[int] = None
    target_reps: Optional[int] = None


class ExportRoutine(BaseModel):
    name: str
    description: Optional[str] = None
    exercises: List[ExportRoutineExercise] = []


class ExportData(BaseModel):
    """匯出 / 匯入的完整資料結構。"""
    exercises: List[ExerciseCreate]
    workouts: List[ExportWorkout]
    routines: List[ExportRoutine]
