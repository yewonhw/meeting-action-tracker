"""
FastAPI 애플리케이션 진입점.

역할:
- API 서버 인스턴스(app)를 만들고
- CORS(프론트엔드 도메인에서 API 호출 허용)를 설정하고
- 기능별 라우터(예: health)를 /api 아래에 연결한다.
- 기동 시 SQLite 테이블을 준비한다 (init_db).

실행 예:
  uvicorn app.main:app --reload --port 8000
  → app.main 모듈의 app 객체를 띄운다는 뜻
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.action_items import router as action_items_router
from app.api.health import router as health_router
from app.api.meetings import router as meetings_router
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    앱 시작 시 한 번: 테이블이 없으면 생성.
    CRUD API가 없어도 모델이 DB에 반영됐는지 로컬에서 바로 확인 가능하다.
    """
    init_db()
    yield


app = FastAPI(
    title="Meeting Action Tracker API",
    description="REST API for meeting notes and action items",
    version="0.1.0",
    lifespan=lifespan,
)

# 브라우저의 Next.js(localhost:3000)가 FastAPI(localhost:8000)를 호출하려면
# 서로 origin이 다르므로 CORS를 열어줘야 한다.
# (같은 서버에서 nginx로 프록시하면 나중에 완화 가능)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 각 라우터의 경로 앞에 /api를 붙인다.
# health.py의 @router.get("/health") → 최종 URL: GET /api/health
app.include_router(health_router, prefix="/api")
app.include_router(meetings_router, prefix="/api")
app.include_router(action_items_router, prefix="/api")
