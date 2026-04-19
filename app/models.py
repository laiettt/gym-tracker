"""SQLAlchemy ORM models.

資料表結構：
- exercises:        動作庫（深蹲、臥推…）
- routines:         課表範本（PPL、上下肢分化…）
- routine_exercises: 課表包含的動作（多對多）
- workouts:         一次訓練記錄
- sets:             每一組的實際記錄
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow_naive() -> datetime:
    """取代 deprecated 的 datetime.utcnow()。

    保持 naive datetime（tzinfo=None）以維持與既有 DB、前端序列化行為的相容性；
    前端 parseServerDate() 會替無時區字串補上 Z 當 UTC 處理。
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Exercise(Base):
    """動作庫。例：深蹲、臥推、硬舉。"""
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=True)  # 例：胸、背、腿
    equipment = Column(String(50), nullable=True)  # 例：Cable、器械、啞鈴、槓鈴
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive)

    sets = relationship("WorkoutSet", back_populates="exercise")
    routine_exercises = relationship("RoutineExercise", back_populates="exercise")


class Routine(Base):
    """課表範本。例：PPL-Push Day。"""
    __tablename__ = "routines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow_naive)

    routine_exercises = relationship(
        "RoutineExercise",
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.order_index",
    )
    workouts = relationship("Workout", back_populates="routine")


class RoutineExercise(Base):
    """課表包含哪些動作（多對多關聯 + 目標組數/次數）。"""
    __tablename__ = "routine_exercises"

    id = Column(Integer, primary_key=True, index=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_index = Column(Integer, default=0)  # 動作順序
    target_sets = Column(Integer, nullable=True)
    target_reps = Column(Integer, nullable=True)

    routine = relationship("Routine", back_populates="routine_exercises")
    exercise = relationship("Exercise", back_populates="routine_exercises")


class Workout(Base):
    """一次訓練。"""
    __tablename__ = "workouts"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=_utcnow_naive, index=True)
    routine_id = Column(Integer, ForeignKey("routines.id"), nullable=True)
    notes = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=True)

    routine = relationship("Routine", back_populates="workouts")
    sets = relationship(
        "WorkoutSet",
        back_populates="workout",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )


class WorkoutSet(Base):
    """每一組的實際記錄。

    注意：類別命名為 WorkoutSet（不叫 Set），避免和 Python 內建 set 衝突。
    資料表名稱 sets 不受影響。
    """
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False, index=True)
    set_number = Column(Integer, nullable=False)  # 這個動作的第幾組
    weight = Column(Float, nullable=True)  # 公斤
    reps = Column(Integer, nullable=True)  # 留空表示力竭
    rpe = Column(Float, nullable=True)  # Rate of Perceived Exertion 1-10
    notes = Column(String(200), nullable=True)

    workout = relationship("Workout", back_populates="sets")
    exercise = relationship("Exercise", back_populates="sets")
