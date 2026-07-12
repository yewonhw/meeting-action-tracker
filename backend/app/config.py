"""
앱 설정값.

환경변수(.env)를 읽어온다.
비밀키·DB 경로는 코드에 하드코딩하지 않고 여기서만 참조한다.
"""

from pathlib import Path

from dotenv import load_dotenv
import os

# backend/ 기준으로 .env를 찾는다 (레포 루트 .env도 허용)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent

# 레포 루트 → backend 순으로 로드 (뒤에 나온 값이 우선되지 않게 루트 먼저)
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_BACKEND_DIR / ".env")

# SQLite 기본 경로: backend/data/meeting_action_tracker.db
# check_same_thread=False 는 FastAPI에서 요청마다 다른 스레드가 DB를 쓸 수 있게 함
_DEFAULT_SQLITE_PATH = _BACKEND_DIR / "data" / "meeting_action_tracker.db"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_SQLITE_PATH}",
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "google/gemma-4-26b-a4b-it:free",
)
