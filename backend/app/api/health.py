from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Liveness check for local/dev and load balancers."""
    return {"status": "ok"}
