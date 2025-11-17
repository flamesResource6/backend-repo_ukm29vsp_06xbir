from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, validator


class MoodEntry(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    mood: str = Field(..., description="mood keyword, e.g., happy, sad, etc.")
    note: Optional[str] = Field(None, description="optional note")

    @validator("date")
    def validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except Exception:
            raise ValueError("date must be YYYY-MM-DD")
        return v

    @validator("mood")
    def validate_mood(cls, v: str) -> str:
        allowed = {"ecstatic", "happy", "neutral", "sad", "down", "angry"}
        if v not in allowed:
            raise ValueError(f"mood must be one of {sorted(allowed)}")
        return v
