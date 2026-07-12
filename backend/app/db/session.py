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
    # SQLite URL이 아니면 폴더를 만들 필요가 없다.
    if not url.startswith("sqlite:///"):
        return
    # sqlite:////absolute 또는 sqlite:///relative
    # 접두사 sqlite:/// 를 제거해 실제 파일 경로 문자열을 얻는다.
    raw_path = url.removeprefix("sqlite:///")
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        # backend/ 에서 uvicorn을 띄운다고 가정한 상대경로
        db_path = Path.cwd() / db_path
    # 부모 디렉터리(예: data/)가 없으면 생성한다.
    db_path.parent.mkdir(parents=True, exist_ok=True)


# 모듈을 불러올 때 DB 파일이 들어갈 폴더를 미리 준비한다.
_ensure_sqlite_directory(DATABASE_URL)

# SQLite는 기본적으로 같은 스레드만 연결을 허용한다.
# FastAPI는 워커 스레드에서 세션을 열 수 있으므로 이 옵션이 필요하다.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# DB에 연결하는 엔진. 이후 Session이 이 엔진을 통해 쿼리를 실행한다.
engine = create_engine(DATABASE_URL, connect_args=_connect_args)

# 세션 팩토리. autocommit/autoflush를 끄고 명시적 commit을 쓴다.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Depends(get_db)용.
    요청이 끝나면 세션을 반드시 close 한다.
    """
    db = SessionLocal()
    try:
        # yield: 엔드포인트가 이 세션을 쓰는 동안 대기한다.
        yield db
    finally:
        # 요청이 성공하든 실패하든 세션을 닫아 연결을 반환한다.
        db.close()


def init_db() -> None:
    """
    모델 모듈을 import 한 뒤 create_all 한다.
    import가 있어야 Base.metadata에 테이블이 등록된다.
    """
    # noqa: F401 — 사이드 이펙트(테이블 등록)를 위한 import
    from app.db import models  # noqa: F401

    # metadata에 등록된 테이블이 DB에 없으면 생성한다. 이미 있으면 건드리지 않는다.
    Base.metadata.create_all(bind=engine)
