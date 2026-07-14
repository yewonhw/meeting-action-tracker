"""
ActionItem 목록(필터·정렬) + 단건 수정·삭제.

경로 (main에서 /api prefix):
  GET    /action-items?assignee=&status=&due_to=&sort_by=&sort_dir=
  PATCH  /action-items/{action_item_id}
  DELETE /action-items/{action_item_id}

왜 목록 API 를 여기에 추가했나?
------------------------------------------------------------
- 담당자/기한/상태 필터·정렬을 프론트 array.filter 이 아니라 DB 쿼리로 처리하기 위함
- 잘못하면: GET 으로 전체 액션을 받은 뒤 JS 에서 거름 → 데이터 늘면 느리고,
  필터 조건이 클라이언트마다 어긋날 수 있음
- 그래서: Query 파라미터 → SQLAlchemy WHERE / ORDER BY → 이미 걸러진 목록만 응답

생성은 여전히 nested:
  POST /meetings/{meeting_id}/action-items
  (소속 회의가 명확해야 해서 단건 컬렉션에는 두지 않음)
"""

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from app.db.models import ActionItem, Meeting
from app.db.session import get_db
from app.schemas.meeting import (
    ActionItemListItem,
    ActionItemRead,
    ActionItemUpdate,
    ActionSortBy,
    SortDir,
)

router = APIRouter(tags=["action-items"])


def _get_action_item_or_404(db: Session, action_item_id: int) -> ActionItem:
    # 단건 PATCH/DELETE 공통. 없으면 404.
    item = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found",
        )
    return item


@router.get("/action-items", response_model=list[ActionItemListItem])
def list_action_items(
    db: Session = Depends(get_db),
    assignee: Optional[str] = Query(
        None,
        description="담당자 부분 일치(대소문자 무시). 비우면 담당자 필터 없음.",
    ),
    # 파라미터 이름을 status 로 열고 싶지만, fastapi.status 모듈과 이름이 겹침
    # → 파이썬 인자는 status_filter, OpenAPI/쿼리 키는 alias="status"
    status_filter: Optional[Literal["todo", "done"]] = Query(
        None,
        alias="status",
        description="todo | done",
    ),
    due_to: Optional[date] = Query(
        None,
        description="기한 상한(이하). YYYY-MM-DD. 예: 오늘 → 오늘까지·지난 기한.",
    ),
    sort_by: ActionSortBy = Query(
        "due_date",
        description="due_date | assignee | status | created_at",
    ),
    sort_dir: SortDir = Query("asc", description="asc | desc"),
) -> list[ActionItemListItem]:
    """
    여러 회의의 액션을 서버에서 필터·정렬해 반환한다.

    설계 메모:
    - 회의 상세의 action_items 는 "한 회의 안" 목록
    - 이 엔드포인트는 "회의를 가로지르는" 목록 (액션 보드용)
    - meeting_title 은 N+1 을 피하려고 join 한 번에 가져온다
    - 기한 필터는 due_to 만 (그날까지). 시작일(due_from)은 두지 않음
    """
    # (ActionItem 행, Meeting.title) 튜플로 받는다.
    # title 만 필요해서 Meeting 전체 ORM 을 안 심는다.
    q = db.query(ActionItem, Meeting.title).join(
        Meeting, ActionItem.meeting_id == Meeting.id
    )

    # --- 필터: 값이 있을 때만 WHERE 절을 붙인다 (전부 선택 사항) ---

    if assignee is not None and assignee.strip():
        # 부분 일치: "민수" → "김민수", "민수님" 도 걸리게
        needle = assignee.strip().lower()
        # SQLite 는 ILIKE 가 약해서 lower() + contains 로 대소문자 무시
        q = q.filter(func.lower(ActionItem.assignee).contains(needle))

    if status_filter is not None:
        q = q.filter(ActionItem.status == status_filter)

    if due_to is not None:
        # 기한 없는 행은 비교 대상이 아니므로 제외
        # due_to=오늘 → 오늘까지(지난 기한 포함)
        q = q.filter(
            ActionItem.due_date.is_not(None),
            ActionItem.due_date <= due_to,
        )

    # --- 정렬: 컬럼 화이트리스트 ---
    sort_columns = {
        "due_date": ActionItem.due_date,
        "assignee": ActionItem.assignee,
        "status": ActionItem.status,
        "created_at": ActionItem.created_at,
    }
    col = sort_columns[sort_by]
    direction = asc if sort_dir == "asc" else desc

    if sort_by == "due_date":
        # null 기한은 뒤로
        q = q.order_by(ActionItem.due_date.is_(None), direction(col), ActionItem.id.asc())
    else:
        q = q.order_by(direction(col), ActionItem.id.asc())

    rows = q.all()
    return [
        ActionItemListItem(
            id=item.id,
            meeting_id=item.meeting_id,
            meeting_title=title,
            task=item.task,
            assignee=item.assignee,
            due_date=item.due_date,
            status=item.status,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        for item, title in rows
    ]


@router.patch("/action-items/{action_item_id}", response_model=ActionItemRead)
def update_action_item(
    action_item_id: int,
    payload: ActionItemUpdate,
    db: Session = Depends(get_db),
) -> ActionItem:
    item = _get_action_item_or_404(db, action_item_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/action-items/{action_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action_item(action_item_id: int, db: Session = Depends(get_db)) -> None:
    item = _get_action_item_or_404(db, action_item_id)
    db.delete(item)
    db.commit()
