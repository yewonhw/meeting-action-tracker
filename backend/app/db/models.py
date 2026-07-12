"""
관계형 데이터 모델.

핵심 관계:
  Meeting (회의록) 1 ──< ActionItem (액션아이템) N

왜 한 테이블로 안 합치나?
- 회의록 원문·결정사항·논의사항은 "회의 1건"의 속성
- 할일·담당자·기한·완료여부는 "액션 N건"으로 따로 조회·수정·필터해야 함
- 과제 요건: 평평한 단일 테이블이 아니라 관계로 모델링

AI 관련 필드 (ai_status 등):
- 구조화는 비동기로 돌리고, 성공했다고 가정하지 않기 위해 상태를 둔다.
- 실제 AI 호출은 이후 커밋. 지금은 스키마만 준비.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Meeting(Base):
    """
    회의록 1건.

    raw_text: 사용자가 붙여넣은 원문 (AI 입력)
    decisions / discussions: AI가 뽑은 결정·논의 (JSON 문자열로 저장 예정)
    action_items: 이 회의에 속한 액션아이템 목록 (1:N)
    """

    # 실제 DB 테이블 이름
    __tablename__ = "meetings"

    # 기본 키. 새 행마다 자동으로 1씩 증가한다.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 회의 제목 (최대 200자). 비어 있으면 안 된다.
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 회의록 원문 전체. Text로 긴 문자열을 담는다.
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    # AI 결과 — 원문에 근거한 내용만 저장. 형식은 이후 서비스에서 JSON으로 강제.
    # 결정사항 JSON 문자열. 구조화 전에는 null일 수 있다.
    decisions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 논의사항 JSON 문자열. 구조화 전에는 null일 수 있다.
    discussions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # pending → processing → done | failed
    # CRUD/AI 커밋에서 로딩·타임아웃·실패 UI와 맞춘다.
    # default: Python에서 새 객체 만들 때, server_default: DB INSERT 시 기본값
    ai_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    # 구조화 실패 시 오류 메시지. 성공 시에는 null이다.
    ai_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 생성 시각. DB가 INSERT 시점에 채운다.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # 수정 시각. INSERT 시 기본값, UPDATE 시 onupdate로 갱신된다.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # cascade: 회의 삭제 시 소속 액션아이템도 함께 삭제
    # passive_deletes와 DB ON DELETE CASCADE를 쓰면 더 명시적이지만,
    # SQLite + ORM cascade로 우선 단순하게 유지한다.
    # back_populates: ActionItem.meeting과 양방향 연결을 맞춘다.
    action_items: Mapped[list[ActionItem]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
    )


class ActionItem(Base):
    """
    액션아이템 N건 (회의록에 종속).

    assignee / due_date:
    - 원문에 없으면 null 허용 (hallucination 방지 — AI가 지어내지 않음)
    status:
    - todo | done (완료 체크는 권장 기능, 스키마만 미리 둠)
    """

    __tablename__ = "action_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # FK: 어떤 회의의 액션인지. 관계의 핵심 컬럼.
    # ondelete="CASCADE": 부모 회의가 삭제되면 DB에서도 이 행을 함께 삭제한다.
    # index=True: meeting_id로 자주 조회하므로 인덱스를 둔다.
    meeting_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 할 일 본문
    task: Mapped[str] = mapped_column(String(500), nullable=False)
    # 담당자. 없으면 null
    assignee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 기한(날짜만). 없으면 null
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # 완료 여부. 기본값은 todo
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="todo",
        server_default="todo",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # 부모 Meeting으로 역참조. Meeting.action_items와 짝을 이룬다.
    meeting: Mapped[Meeting] = relationship(back_populates="action_items")
