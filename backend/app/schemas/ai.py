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
    # 할 일 본문. 비어 있으면 안 되고, 최대 500자까지 허용한다.
    task: str = Field(..., min_length=1, max_length=500)
    # 담당자. 원문에 없으면 null이다 한다.
    assignee: Optional[str] = Field(None, max_length=100)
    # 기한. YYYY-MM-DD 형식의 date이거나 null이다 한다.
    due_date: Optional[date] = None

    @field_validator("assignee", mode="before")
    @classmethod
    def empty_assignee_to_none(cls, value: object) -> object:
        # 모델이 "" 또는 공백만 보내면 None으로 바꾼다.
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("due_date", mode="before")
    @classmethod
    def empty_due_date_to_none(cls, value: object) -> object:
        # 기한도 빈 문자열이면 None으로 통일한다.
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


class AiStructureResult(BaseModel):
    """회의록 구조화 결과. 원문에 없는 내용은 넣지 않는다."""

    # 결정사항 목록. 없으면 빈 리스트다.
    decisions: list[str] = Field(default_factory=list)
    # 논의사항 목록. 없으면 빈 리스트다.
    discussions: list[str] = Field(default_factory=list)
    # 액션아이템 목록. 없으면 빈 리스트다.
    action_items: list[AiActionItem] = Field(default_factory=list)

    @field_validator("decisions", "discussions", mode="before")
    @classmethod
    def coerce_str_list(cls, value: object) -> object:
        # 모델이 null을 보내면 빈 리스트로 바꿔 이후 처리를 단순하게 한다.
        if value is None:
            return []
        return value
