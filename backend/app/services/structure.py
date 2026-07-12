"""
회의록 AI 구조화 서비스.

흐름:
1. meeting.ai_status = processing
2. OpenRouter 호출 → JSON 문자열
3. AiStructureResult로 검증
4. decisions/discussions/action_items 저장
5. ai_status = done | failed
"""

from __future__ import annotations

import json

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.models import ActionItem, Meeting
from app.schemas.ai import AiStructureResult
from app.services.openrouter import OpenRouterError, complete_meeting_structure


class StructureError(Exception):
    """구조화 실패 (호출/검증). 호출부가 ai_error에 메시지를 넣는다."""


async def structure_meeting(db: Session, meeting: Meeting) -> Meeting:
    # 구조화 시작: 상태를 processing으로 바꾸고, 이전 오류 메시지를 지운다.
    meeting.ai_status = "processing"
    meeting.ai_error = None
    db.commit()

    try:
        # OpenRouter에 원문(과 제목)을 보내고 JSON 문자열을 받는다.
        raw_json = await complete_meeting_structure(
            meeting.raw_text,
            title=meeting.title,
        )
        try:
            # 문자열을 Python 객체(dict/list)로 파싱한다.
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise StructureError(f"Model returned invalid JSON: {exc}") from exc

        try:
            # Pydantic 스키마로 필드·타입·제약을 검증한다.
            result = AiStructureResult.model_validate(parsed)
        except ValidationError as exc:
            raise StructureError(f"JSON failed schema validation: {exc}") from exc

        # 결정·논의는 DB Text 컬럼에 JSON 문자열로 저장한다.
        # ensure_ascii=False 로 한글이 유니코드 이스케이프되지 않게 한다.
        meeting.decisions = json.dumps(result.decisions, ensure_ascii=False)
        meeting.discussions = json.dumps(result.discussions, ensure_ascii=False)

        # AI 결과로 액션아이템을 교체
        # 기존 목록을 비운 뒤, 새 항목을 하나씩 붙인다.
        meeting.action_items.clear()
        for item in result.action_items:
            meeting.action_items.append(
                ActionItem(
                    task=item.task,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    # AI가 만든 항목은 항상 미완료(todo)로 시작한다.
                    status="todo",
                )
            )

        # 성공: 상태를 done으로 두고 오류 필드를 비운다.
        meeting.ai_status = "done"
        meeting.ai_error = None
        db.commit()
        # DB가 채운 id·타임스탬프 등을 ORM 객체에 다시 읽어 온다.
        db.refresh(meeting)
        return meeting

    except (OpenRouterError, StructureError) as exc:
        # 호출 실패 또는 JSON/스키마 검증 실패: failed와 오류 메시지를 저장한다.
        meeting.ai_status = "failed"
        meeting.ai_error = str(exc)
        db.commit()
        db.refresh(meeting)
        # 호출부(API)에서 HTTP 상태 코드로 바꿀 수 있도록 예외를 다시 던진다.
        raise
