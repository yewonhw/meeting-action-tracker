"""
회의록 AI 구조화 서비스 (비동기 백그라운드 작업).

동기(예전)과 다른 점:
- API 요청은 "시작만" 하고 바로 응답한다
- 실제 OpenRouter 호출은 백그라운드에서 한다
- 프론트/클라이언트는 GET /meetings/{id} 로 ai_status 를 반복해서 확인한다

상태 흐름:
  pending → processing → done
                      ↘ failed  (검증 실패, API 오류, 타임아웃 등)
"""

from __future__ import annotations

import json
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session, selectinload

from app.db.models import ActionItem, Meeting
from app.db.session import SessionLocal
from app.schemas.ai import AiStructureResult
from app.services.openrouter import OpenRouterError, complete_meeting_structure

# 이 파일에서 나는 로그를 찍을 때 쓰는 이름표
logger = logging.getLogger(__name__)


class StructureError(Exception):
    """JSON 깨짐·스키마 검증 실패처럼 'AI 응답 내용' 문제일 때 쓰는 에러."""


def begin_structure(db: Session, meeting: Meeting) -> Meeting:
    """
    구조화를 '시작'만 표시한다. (아직 AI는 안 부름)

    API 요청 스레드에서 호출한다.
    processing 으로 바꿔야 다른 요청이 중복으로 시작하지 못한다.
    """
    # 상태: 처리 중
    meeting.ai_status = "processing"
    # 예전에 남아 있던 실패 메시지 지우기
    meeting.ai_error = None
    # DB에 바로 저장 (다른 GET 요청이 processing 을 볼 수 있게)
    db.commit()
    # id 등 최신 값 다시 읽기
    db.refresh(meeting)
    return meeting


async def _structure_meeting_in_session(db: Session, meeting: Meeting) -> None:
    """
    이미 열린 DB 세션과 Meeting 객체로 실제 구조화를 수행한다.

    성공 → ai_status=done + 결과 저장
    실패 → ai_status=failed + ai_error 저장
    (이 함수 안에서는 HTTPException 을 만들지 않는다. 백그라운드라서 클라이언트가 못 받음)
    """
    try:
        # 1) OpenRouter 에 원문 보내기 → JSON 글자 받기
        #    (타임아웃은 openrouter 클라이언트의 httpx timeout 이 담당)
        raw_json = await complete_meeting_structure(
            meeting.raw_text,
            title=meeting.title,
        )

        # 2) 글자 → dict
        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise StructureError(f"Model returned invalid JSON: {exc}") from exc

        # 3) 스키마 검사
        try:
            result = AiStructureResult.model_validate(parsed)
        except ValidationError as exc:
            raise StructureError(f"JSON failed schema validation: {exc}") from exc

        # 4) 결정/논의 저장 (리스트를 JSON 문자열로)
        meeting.decisions = json.dumps(result.decisions, ensure_ascii=False)
        meeting.discussions = json.dumps(result.discussions, ensure_ascii=False)

        # 5) 액션아이템을 AI 결과로 교체
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

        # 6) 성공
        meeting.ai_status = "done"
        meeting.ai_error = None
        db.commit()

    except (OpenRouterError, StructureError) as exc:
        # 예상 가능한 실패: 상태만 failed 로 남기고 끝
        # (백그라운드에서는 raise 하지 않아도 되지만, 로그는 남긴다)
        meeting.ai_status = "failed"
        meeting.ai_error = str(exc)
        db.commit()
        logger.warning("structure failed meeting_id=%s: %s", meeting.id, exc)

    except Exception as exc:
        # 예상 못 한 예외도 failed 로 기록 (서버만 조용히 죽지 않게)
        meeting.ai_status = "failed"
        meeting.ai_error = f"Unexpected error: {exc}"
        db.commit()
        logger.exception("structure unexpected error meeting_id=%s", meeting.id)


async def run_structure_job(meeting_id: int) -> None:
    """
    BackgroundTasks 에서 실행되는 작업 함수.

    중요:
    - 요청용 DB 세션은 응답 후 닫히므로, 여기서 새 세션을 연다
    - ORM 객체를 인자로 받지 않고 meeting_id 만 받는다
      (닫힌 세션에 묶인 객체는 위험함)
    """
    # 새 DB 세션 열기
    db = SessionLocal()
    try:
        # 회의 + 액션아이템을 다시 조회
        meeting = (
            db.query(Meeting)
            .options(selectinload(Meeting.action_items))
            .filter(Meeting.id == meeting_id)
            .first()
        )
        # 그사이에 삭제됐으면 할 일 없음
        if meeting is None:
            logger.warning("structure job skipped: meeting %s not found", meeting_id)
            return

        # 실제 구조화 수행
        await _structure_meeting_in_session(db, meeting)
    finally:
        # 세션은 무조건 닫기 (연결 누수 방지)
        db.close()
