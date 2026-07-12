"""
OpenRouter가 돌려줘야 하는 JSON 스키마.

모델 응답을 이 Pydantic 모델로 검증한다.
검증 실패 = 형식 오류로 보고 ai_status=failed 처리.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AiActionItem(BaseModel):
    task: str = Field(..., min_length=1, max_length=500)
    assignee: Optional[str] = Field(None, max_length=100)
    due_date: Optional[date] = None

    @field_validator("assignee", mode="before")
    @classmethod
    def empty_assignee_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("due_date", mode="before")
    @classmethod
    def empty_due_date_to_none(cls, value: object) -> object:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AiStructureResult(BaseModel):
    """회의록 구조화 결과. 원문에 없는 내용은 넣지 않는다."""

    decisions: list[str] = Field(default_factory=list)
    discussions: list[str] = Field(default_factory=list)
    action_items: list[AiActionItem] = Field(default_factory=list)

    @field_validator("decisions", "discussions", mode="before")
    @classmethod
    def coerce_str_list(cls, value: object) -> object:
        if value is None:
            return []
        return value
