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
    meeting.ai_status = "processing"
    meeting.ai_error = None
    db.commit()

    try:
        raw_json = await complete_meeting_structure(
            meeting.raw_text,
            title=meeting.title,
        )
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise StructureError(f"Model returned invalid JSON: {exc}") from exc

        try:
            result = AiStructureResult.model_validate(parsed)
        except ValidationError as exc:
            raise StructureError(f"JSON failed schema validation: {exc}") from exc

        meeting.decisions = json.dumps(result.decisions, ensure_ascii=False)
        meeting.discussions = json.dumps(result.discussions, ensure_ascii=False)

        # AI 결과로 액션아이템을 교체
        meeting.action_items.clear()
        for item in result.action_items:
            meeting.action_items.append(
                ActionItem(
                    task=item.task,
                    assignee=item.assignee,
                    due_date=item.due_date,
                    status="todo",
                )
            )

        meeting.ai_status = "done"
        meeting.ai_error = None
        db.commit()
        db.refresh(meeting)
        return meeting

    except (OpenRouterError, StructureError) as exc:
        meeting.ai_status = "failed"
        meeting.ai_error = str(exc)
        db.commit()
        db.refresh(meeting)
        raise
