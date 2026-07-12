"""
Meeting CRUD + AI 구조화 트리거.

경로 (main에서 /api prefix):
  POST   /meetings
  GET    /meetings
  GET    /meetings/{meeting_id}
  PATCH  /meetings/{meeting_id}
  DELETE /meetings/{meeting_id}
  POST   /meetings/{meeting_id}/action-items
  POST   /meetings/{meeting_id}/structure
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.db.models import ActionItem, Meeting
from app.db.session import get_db
from app.schemas.meeting import (
    ActionItemCreate,
    ActionItemRead,
    MeetingCreate,
    MeetingListItem,
    MeetingRead,
    MeetingUpdate,
)
from app.services.openrouter import OpenRouterError
from app.services.structure import StructureError, structure_meeting

# 이 파일의 엔드포인트를 묶는 라우터. OpenAPI 문서에서 meetings 그룹으로 보인다.
router = APIRouter(tags=["meetings"])


def _get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    # id로 회의를 찾고, 없으면 404를 낸다.
    # selectinload로 action_items를 미리 불러 MeetingRead 응답에 포함한다.
    meeting = (
        db.query(Meeting)
        .options(selectinload(Meeting.action_items))
        .filter(Meeting.id == meeting_id)
        .first()
    )
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return meeting


@router.post("/meetings", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreate, db: Session = Depends(get_db)) -> Meeting:
    # 요청 본문의 제목·원문으로 새 Meeting 행을 만든다.
    meeting = Meeting(title=payload.title, raw_text=payload.raw_text)
    db.add(meeting)
    db.commit()
    # commit 후 DB가 채운 id 등을 객체에 반영한다.
    db.refresh(meeting)
    # action_items가 로드된 형태로 다시 조회해 응답한다.
    return _get_meeting_or_404(db, meeting.id)


@router.get("/meetings", response_model=list[MeetingListItem])
def list_meetings(db: Session = Depends(get_db)) -> list[Meeting]:
    # 최신 생성 순으로 회의 목록을 반환한다. 목록용 스키마는 가벼운 필드만 쓴다.
    return db.query(Meeting).order_by(Meeting.created_at.desc()).all()


@router.get("/meetings/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> Meeting:
    # 단건 조회. 없으면 404.
    return _get_meeting_or_404(db, meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=MeetingRead)
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdate,
    db: Session = Depends(get_db),
) -> Meeting:
    meeting = _get_meeting_or_404(db, meeting_id)
    # exclude_unset=True: 요청에 실제로 온 필드만 반영한다 (부분 수정).
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(meeting, key, value)
    db.commit()
    return _get_meeting_or_404(db, meeting_id)


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)) -> None:
    # 회의를 삭제한다. cascade 설정으로 소속 액션아이템도 함께 삭제된다.
    meeting = _get_meeting_or_404(db, meeting_id)
    db.delete(meeting)
    db.commit()


@router.post(
    "/meetings/{meeting_id}/action-items",
    response_model=ActionItemRead,
    status_code=status.HTTP_201_CREATED,
)
def create_action_item(
    meeting_id: int,
    payload: ActionItemCreate,
    db: Session = Depends(get_db),
) -> ActionItem:
    # 존재 확인 (액션 없이 가볍게)
    # Meeting 전체 대신 id만 조회해 회의가 있는지 확인한다.
    exists = db.query(Meeting.id).filter(Meeting.id == meeting_id).first()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    # 해당 회의에 속한 새 액션아이템을 만든다.
    item = ActionItem(
        meeting_id=meeting_id,
        task=payload.task,
        assignee=payload.assignee,
        due_date=payload.due_date,
        status=payload.status,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/meetings/{meeting_id}/structure",
    response_model=MeetingRead,
)
async def structure_meeting_endpoint(
    meeting_id: int,
    db: Session = Depends(get_db),
) -> Meeting:
    """
    회의록 원문을 OpenRouter로 구조화한다.
    성공 시 decisions/discussions/action_items 저장, ai_status=done.
    실패 시 ai_status=failed, ai_error에 사유 저장 후 에러 응답.
    """
    meeting = _get_meeting_or_404(db, meeting_id)
    # 이미 구조화 중이면 중복 요청을 막고 409를 반환한다.
    if meeting.ai_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting is already being structured",
        )

    try:
        # 실제 AI 호출·검증·저장은 structure 서비스에 위임한다.
        await structure_meeting(db, meeting)
    except OpenRouterError as exc:
        # 외부 API 실패 → 502 (게이트웨이/업스트림 오류)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except StructureError as exc:
        # JSON·스키마 검증 실패 → 422 (처리할 수 없는 내용)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    # 최신 상태와 액션아이템을 다시 읽어 반환한다.
    return _get_meeting_or_404(db, meeting_id)
