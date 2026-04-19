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


class ReorderSetsRequest(BaseModel):
    set_ids: List[int]


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


# ========== 結束訓練的分析 ==========
class ExerciseAnalysis(BaseModel):
    """單一動作的本次表現與近期趨勢。"""
    exercise_id: int
    exercise_name: str
    today_max_weight: Optional[float] = None
    today_max_weight_reps: Optional[int] = None
    previous_max_weight: Optional[float] = None  # 此次以前該動作的歷史最大重量
    is_pr: bool = False
    is_stagnant: bool = False     # 連續 3+ 次同重量，建議漸進加重
    is_below_recent: bool = False  # 今日最大重量低於近 3 次
    suggestion: Optional[str] = None  # 彙整一句話給前端直接顯示


class WorkoutAnalysis(BaseModel):
    workout_id: int
    date: datetime
    total_volume: float
    total_sets: int
    total_reps: int
    muscle_groups: List[str]
    previous_same_group_volume: Optional[float] = None
    volume_delta_pct: Optional[float] = None  # (today - prev) / prev * 100
    exercises: List[ExerciseAnalysis] = []


# ========== 月度分析 ==========
class MonthlyMuscleGroup(BaseModel):
    category: str
    sets_count: int
    volume: float
    percentage: float  # 佔總量百分比


class MonthlyTopExercise(BaseModel):
    exercise_id: int
    exercise_name: str
    sets_count: int
    total_volume: float
    max_weight: Optional[float] = None


class MonthlyAnalytics(BaseModel):
    year: int
    month: int
    is_current_month: bool  # 當月還沒結束時為 True，前端標示「本月進度」
    training_days: int
    total_workouts: int
    total_sets: int
    total_reps: int
    total_volume: float
    avg_duration_minutes: Optional[float] = None
    muscle_groups: List[MonthlyMuscleGroup] = []
    top_exercises: List[MonthlyTopExercise] = []
    pr_count: int = 0
    pr_exercise_names: List[str] = []
    prev_month_total_volume: Optional[float] = None
    volume_delta_pct: Optional[float] = None  # vs 上個月
    suggestions: List[str] = []  # 下月建議（由後端根據資料產生）


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
