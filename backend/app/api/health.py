"""
헬스체크 API.

서버가 살아 있는지 확인하는 최소 엔드포인트.
배포/로드밸런서 점검, 로컬에서 FE↔BE 연결 확인용으로 쓴다.
비즈니스 로직(회의록, AI)은 여기에 두지 않는다.
"""

from fastapi import APIRouter

# APIRouter: 기능별로 라우트를 모아 main.py에서 한 번에 등록하기 위한 단위
router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check for local/dev and load balancers."""
    # DB·AI 호출 없이 고정 응답만 돌려 서버 기동 여부를 확인한다.
    return {"status": "ok"}
