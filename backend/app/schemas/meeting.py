"""
Meeting / ActionItem API 스키마.

ORM 모델(db/models.py)과 분리한다.
- 요청: 클라이언트가 보낼 수 있는 필드만
- 응답: API로 내보낼 필드만
AI 호출은 이후 커밋. ai_status / ai_error는 읽기 전용.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# AI 구조화 상태. 이 네 값만 허용한다.
AiStatus = Literal["pending", "processing", "done", "failed"]
# 액션아이템 완료 상태.
ActionStatus = Literal["todo", "done"]


class ActionItemCreate(BaseModel):
    # 새 액션아이템 생성 요청 본문
    task: str = Field(..., min_length=1, max_length=500)
    assignee: Optional[str] = Field(None, max_length=100)
    due_date: Optional[date] = None
    # 생략하면 기본값 todo
    status: ActionStatus = "todo"


class ActionItemUpdate(BaseModel):
    # 부분 수정: 보낸 필드만 바뀐다. 모두 Optional이다
    task: Optional[str] = Field(None, min_length=1, max_length=500)
    assignee: Optional[str] = Field(None, max_length=100)
    due_date: Optional[date] = None
    status: Optional[ActionStatus] = None


class ActionItemRead(BaseModel):
    # ORM 객체를 이 스키마로 변환할 수 있게 한다 (from_attributes).
    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    task: str
    assignee: Optional[str]
    due_date: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime


class MeetingCreate(BaseModel):
    # 회의 생성 시 클라이언트가 보내는 필드만 받는다.
    title: str = Field(..., min_length=1, max_length=200)
    raw_text: str = Field(..., min_length=1)


class MeetingUpdate(BaseModel):
    """수동 검토·수정용. AI 상태 필드는 여기서 바꾸지 않는다."""

    # 부분 수정용. 제목·원문·결정·논의만 수동으로 고칠 수 있다.
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    raw_text: Optional[str] = Field(None, min_length=1)
    decisions: Optional[str] = None
    discussions: Optional[str] = None


class MeetingRead(BaseModel):
    # 단건 조회·생성·수정 응답. 액션아이템 목록을 포함한다.
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    raw_text: str
    decisions: Optional[str]
    discussions: Optional[str]
    ai_status: str
    ai_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    # 기본값은 빈 리스트. 액션이 없어도 항상 리스트로 응답한다.
    action_items: list[ActionItemRead] = []


class MeetingListItem(BaseModel):
    """목록용 — 원문·액션아이템은 빼고 가볍게."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    ai_status: str
    created_at: datetime
    updated_at: datetime
