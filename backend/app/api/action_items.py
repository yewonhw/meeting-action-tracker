"""
ActionItem 단건 수정·삭제.

경로 (main에서 /api prefix):
  PATCH  /action-items/{action_item_id}
  DELETE /action-items/{action_item_id}

생성은 회의 소속이 분명해야 해서
POST /meetings/{meeting_id}/action-items 에 둔다.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import ActionItem
from app.db.session import get_db
from app.schemas.meeting import ActionItemRead, ActionItemUpdate

router = APIRouter(tags=["action-items"])


def _get_action_item_or_404(db: Session, action_item_id: int) -> ActionItem:
    item = db.query(ActionItem).filter(ActionItem.id == action_item_id).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action item not found",
        )
    return item


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
