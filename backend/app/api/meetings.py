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

router = APIRouter(tags=["meetings"])


def _get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
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
    meeting = Meeting(title=payload.title, raw_text=payload.raw_text)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _get_meeting_or_404(db, meeting.id)


@router.get("/meetings", response_model=list[MeetingListItem])
def list_meetings(db: Session = Depends(get_db)) -> list[Meeting]:
    return db.query(Meeting).order_by(Meeting.created_at.desc()).all()


@router.get("/meetings/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> Meeting:
    return _get_meeting_or_404(db, meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=MeetingRead)
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdate,
    db: Session = Depends(get_db),
) -> Meeting:
    meeting = _get_meeting_or_404(db, meeting_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(meeting, key, value)
    db.commit()
    return _get_meeting_or_404(db, meeting_id)


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)) -> None:
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
    exists = db.query(Meeting.id).filter(Meeting.id == meeting_id).first()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

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
    if meeting.ai_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting is already being structured",
        )

    try:
        await structure_meeting(db, meeting)
    except OpenRouterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except StructureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _get_meeting_or_404(db, meeting_id)
