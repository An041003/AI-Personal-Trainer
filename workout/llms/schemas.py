from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


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
    session_minutes: int = Field(ge=5, le=240)
    split: str
    days: List[DayPlan]
