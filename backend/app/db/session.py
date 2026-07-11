"""
DB 세션/엔진.

역할:
- SQLAlchemy Engine 생성 (SQLite 파일에 연결)
- 요청 단위 Session 제공 (의존성 주입용 get_db)
- 앱 기동 시 테이블 생성 (create_all)

Alembic 마이그레이션은 아직 쓰지 않는다.
과제 우선순위상 "관계형 모델 + 동작"이 먼저이고,
스키마 변경 이력이 필요해지면 그때 추가한다.
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL


class Base(DeclarativeBase):
    """모든 ORM 모델의 공통 부모. metadata에 테이블 정의가 모인다."""


def _ensure_sqlite_directory(url: str) -> None:
    """
    sqlite:///./data/foo.db 처럼 파일 경로일 때
    data/ 폴더가 없으면 만들어 둔다. (파일 자체는 SQLite가 생성)
    """
    if not url.startswith("sqlite:///"):
        return
    # sqlite:////absolute 또는 sqlite:///relative
    raw_path = url.removeprefix("sqlite:///")
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        # backend/ 에서 uvicorn을 띄운다고 가정한 상대경로
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(DATABASE_URL)

# SQLite는 기본적으로 같은 스레드만 연결을 허용한다.
# FastAPI는 워커 스레드에서 세션을 열 수 있으므로 이 옵션이 필요하다.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Depends(get_db)용.
    요청이 끝나면 세션을 반드시 close 한다.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    모델 모듈을 import 한 뒤 create_all 한다.
    import가 있어야 Base.metadata에 테이블이 등록된다.
    """
    # noqa: F401 — 사이드 이펙트(테이블 등록)를 위한 import
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
