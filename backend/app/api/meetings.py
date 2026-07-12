"""
Meeting CRUD + AI 구조화 트리거 (비동기).

경로 (main에서 /api prefix):
  POST   /meetings
  GET    /meetings
  GET    /meetings/{meeting_id}
  PATCH  /meetings/{meeting_id}
  DELETE /meetings/{meeting_id}
  POST   /meetings/{meeting_id}/action-items
  POST   /meetings/{meeting_id}/structure   ← 202 Accepted, 백그라운드 실행
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
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
from app.services.structure import begin_structure, run_structure_job

# OpenAPI(Swagger)에서 meetings 그룹으로 보이게
router = APIRouter(tags=["meetings"])


def _get_meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    """
    id로 회의 1개를 찾는다.
    없으면 404.
    액션아이템도 같이 불러 MeetingRead 응답에 넣는다.
    """
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
    """새 회의 만들기. 201 = Created."""
    meeting = Meeting(title=payload.title, raw_text=payload.raw_text)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return _get_meeting_or_404(db, meeting.id)


@router.get("/meetings", response_model=list[MeetingListItem])
def list_meetings(db: Session = Depends(get_db)) -> list[Meeting]:
    """회의 목록. 최신 생성이 위로."""
    return db.query(Meeting).order_by(Meeting.created_at.desc()).all()


@router.get("/meetings/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> Meeting:
    """
    회의 상세.
    AI 구조화 중/완료/실패를 확인할 때도 이 주소를 반복 호출(폴링)하면 된다.
    보는 필드: ai_status, ai_error, decisions, discussions, action_items
    """
    return _get_meeting_or_404(db, meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=MeetingRead)
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdate,
    db: Session = Depends(get_db),
) -> Meeting:
    """부분 수정. 요청에 온 필드만 바꾼다."""
    meeting = _get_meeting_or_404(db, meeting_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(meeting, key, value)
    db.commit()
    return _get_meeting_or_404(db, meeting_id)


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)) -> None:
    """회의 삭제. cascade 로 액션아이템도 같이 삭제."""
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
    """회의에 할 일 1개 추가."""
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
    status_code=status.HTTP_202_ACCEPTED,
)
def structure_meeting_endpoint(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Meeting:
    """
    AI 구조화를 '백그라운드'로 시작한다.

    동작:
    1. 이미 processing 이면 409 (중복 시작 금지)
    2. ai_status 를 processing 으로 바꿈
    3. BackgroundTasks 에 실제 AI 작업을 등록
    4. 202 Accepted + 현재 회의 데이터(아직 결과 없을 수 있음)를 바로 반환

    결과는 나중에 GET /meetings/{id} 로 확인:
    - ai_status == "done"  → 성공
    - ai_status == "failed" → ai_error 확인
    - ai_status == "processing" → 아직 진행 중, 다시 조회
    """
    meeting = _get_meeting_or_404(db, meeting_id)

    # 이미 다른 구조화가 돌고 있으면 또 시작하지 않음
    if meeting.ai_status == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Meeting is already being structured",
        )

    # DB에 processing 표시 (폴링하는 쪽이 바로 볼 수 있게)
    begin_structure(db, meeting)

    # 응답을 보낸 뒤에 run_structure_job 이 실행되도록 등록
    # meeting 객체 대신 id 만 넘긴다 (요청 세션이 닫혀도 안전)
    background_tasks.add_task(run_structure_job, meeting_id)

    # 202 + 현재 상태(processing) 반환
    return _get_meeting_or_404(db, meeting_id)
