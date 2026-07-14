"""
Meeting / ActionItem API 스키마.

ORM 모델(db/models.py)과 분리한다.
- 요청: 클라이언트가 보낼 수 있는 필드만
- 응답: API로 내보낼 필드만
AI 호출은 이후 커밋. ai_status / ai_error는 읽기 전용.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


# AI 구조화 상태. 이 네 값만 허용한다.
AiStatus = Literal["pending", "processing", "done", "failed"]
# 액션아이템 완료 상태.
ActionStatus = Literal["todo", "done"]


def serialize_utc_datetime(value: datetime) -> str:
    """
    DB 시각을 API JSON 문자열로 바꿀 때 쓴다.

    SQLite 의 func.now() 는 보통 UTC 인데, 타임존 표시(Z) 없이 나올 수 있다.
    예: "2026-07-12T04:56:54"

    브라우저(JS)는 Z 없는 문자열을 "이미 로컬 시간"으로 읽어서
    한국에서 보면 9시간 어긋난다.

    그래서 naive(타임존 없음) 이면 UTC 로 간주하고 끝에 Z 를 붙인다.
    예: "2026-07-12T04:56:54Z" → 화면에서 오후 1:56 (KST)
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    # +00:00 대신 Z 로 통일 (프론트가 헷갈리지 않게)
    return value.isoformat().replace("+00:00", "Z")


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

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, value: datetime) -> str:
        return serialize_utc_datetime(value)


class ActionItemListItem(BaseModel):
    """
    전체 액션 목록 응답 (GET /action-items).

    ActionItemRead 와 다른 점:
    - meeting_title 추가 → 보드에서 "어느 회의 소속인지"를 바로 보여 주기 위함
    - 회의 상세 안의 action_items[] 는 title 이 필요 없어서 Read 를 그대로 씀

    왜 별도 스키마?
    - 목록/상세 응답 모양이 다르면 스키마를 나누는 편이 API 문서·타입에 덜 헷갈림
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    meeting_id: int
    # join 결과로 API 가 채워 줌 (DB 컬럼이 아님)
    meeting_title: str
    task: str
    assignee: Optional[str]
    due_date: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, value: datetime) -> str:
        return serialize_utc_datetime(value)


# 정렬 허용 값. 쿼리 문자열을 그대로 SQL 컬럼명에 꽂지 않기 위한 화이트리스트.
ActionSortBy = Literal["due_date", "assignee", "status", "created_at"]
SortDir = Literal["asc", "desc"]


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

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, value: datetime) -> str:
        return serialize_utc_datetime(value)


class MeetingListItem(BaseModel):
    """목록용 — 원문·액션아이템은 빼고 가볍게."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    ai_status: str
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, value: datetime) -> str:
        return serialize_utc_datetime(value)
