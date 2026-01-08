from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.domains.workout.contract import MUSCLE_TAXONOMY, GOAL_STYLE_ENUM


# ============================================================
# Workout Plan schema (LLM output for weekly plan)
# ============================================================

class ExerciseItem(BaseModel):
    exercise_id: int = Field(ge=1)
    sets: int = Field(ge=1, le=12)
    reps: str
    rest_sec: int = Field(ge=0, le=600)
    notes: str = ""


class DayPlan(BaseModel):
    day: str
    exercises: List[ExerciseItem]


class WorkoutPlan(BaseModel):
    goal: str
    days_per_week: int = Field(ge=1, le=7)
    session_minutes: int = Field(ge=10, le=240)  # đồng bộ với serializer + planning guard
    split: str
    days: List[DayPlan]


# ============================================================
# Intent → Internal Goal schema (LLM structured output)
# ============================================================

class MuscleEnum(str, Enum):
    chest = "chest"
    shoulders = "shoulders"
    triceps = "triceps"
    back = "back"
    biceps = "biceps"
    quadriceps = "quadriceps"
    hamstrings = "hamstrings"
    hips = "hips"
    calves = "calves"
    core = "core"


class GoalStyleEnum(str, Enum):
    health = "health"
    general_fitness = "general_fitness"
    fat_loss = "fat_loss"
    body_recomposition = "body_recomposition"
    hypertrophy = "hypertrophy"
    strength = "strength"
    endurance = "endurance"
    athletic_performance = "athletic_performance"
    mobility_flexibility = "mobility_flexibility"
    posture_stability = "posture_stability"
    rehab_prevention = "rehab_prevention"
    mixed = "mixed"

class TrainingDayEnum(str, Enum):
    mon = "mon"
    tue = "tue"
    wed = "wed"
    thu = "thu"
    fri = "fri"
    sat = "sat"
    sun = "sun"


# Guard tránh lệch contract về sau
assert tuple(m.value for m in MuscleEnum) == MUSCLE_TAXONOMY, "MuscleEnum lệch MUSCLE_TAXONOMY"
assert tuple(g.value for g in GoalStyleEnum) == GOAL_STYLE_ENUM, "GoalStyleEnum lệch GOAL_STYLE_ENUM"


class MuscleRankItem(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    muscle: MuscleEnum
    rank: int = Field(ge=1)

class WeeklyFocusByDayItem(BaseModel):
    training_day: TrainingDayEnum
    focus: List[MuscleRankItem]


class IntentInternalGoal(BaseModel):
    goal_style: GoalStyleEnum
    priority_targets: List[str] = Field(default_factory=list)
    priority_muscles: List[MuscleEnum] = Field(default_factory=list)

    training_days: List[TrainingDayEnum] = Field(default_factory=list)
    weekly_focus_by_day: List[WeeklyFocusByDayItem] = Field(default_factory=list)
    risk_notes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_weekly_focus(self):
        # 1) training_days unique
        if self.training_days:
            if len(set(self.training_days)) != len(self.training_days):
                raise ValueError("training_days phải unique")

        # 2) weekly_focus_by_day length/unique training_day
        if self.weekly_focus_by_day:
            days = [x.training_day for x in self.weekly_focus_by_day]
            if len(set(days)) != len(days):
                raise ValueError("weekly_focus_by_day.training_day phải unique")

            # nếu training_days có, enforce cùng length và cùng tập ngày
            if self.training_days:
                if len(self.training_days) != len(self.weekly_focus_by_day):
                    raise ValueError("weekly_focus_by_day phải có đúng số ngày bằng training_days")
                if set(self.training_days) != set(days):
                    raise ValueError("training_days và weekly_focus_by_day.training_day phải khớp nhau")

            # validate từng ngày: ranks unique, muscles unique
            for item in self.weekly_focus_by_day:
                focus = item.focus or []
                muscles = [f.muscle for f in focus]
                ranks = [f.rank for f in focus]
                if len(set(muscles)) != len(muscles):
                    raise ValueError("Mỗi ngày không được lặp muscle trong focus")
                if len(set(ranks)) != len(ranks):
                    raise ValueError("Mỗi ngày không được lặp rank trong focus")

        return self

