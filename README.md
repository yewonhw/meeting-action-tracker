# Meeting Action Tracker

회의록 텍스트를 AI로 구조화하고, 결정사항·액션아이템·논의사항을 관리하는 웹 서비스입니다.

## 현재 상태

### 된 것
- Frontend(Next.js) / Backend(FastAPI) monorepo 뼈대
- Backend `GET /api/health` 헬스체크
- SQLite 사용 (별도 DB 서버/Docker 불필요)
- 관계형 데이터 모델: Meeting 1:N ActionItem
- Meeting / ActionItem CRUD API
- 환경변수 예시 (`.env.example`)

### 아직 안 된 것
- AI 구조화 (OpenRouter)
- 비동기 AI 처리 (loading / fail / timeout)
- 실제 화면 플로우
- AWS 배포

## 아키텍처 (예정)

```
Browser → Next.js (frontend)
                │ HTTP
                ▼
         FastAPI (backend) → SQLite (파일 DB)
                │
                ▼
           OpenRouter (LLM)
```

배포 시 EC2 + nginx로 `/` → Next, `/api` → FastAPI 연결 예정.
SQLite 파일은 EC2 디스크(또는 EBS)에 두고 FastAPI가 직접 읽는다.

## 데이터 모델

```
meetings                         action_items
─────────                        ────────────
id (PK)                          id (PK)
title                            meeting_id (FK → meetings.id)
raw_text                         task
decisions (nullable)             assignee (nullable)  ← 원문에 없으면 null
discussions (nullable)           due_date (nullable) ← 원문에 없으면 null
ai_status                        status (todo|done)
ai_error                         created_at / updated_at
created_at / updated_at

Meeting 1 ──────── < ActionItem N
```

- 회의 삭제 시 소속 액션아이템도 함께 삭제 (ORM cascade + FK ON DELETE CASCADE)
- AI 결과 필드는 스키마만 준비. 호출·검증은 이후 커밋

## 스택 선택 이유

| 영역 | 선택 | 이유 |
|------|------|------|
| Frontend | Next.js (App Router) | React 기반 UI·라우팅을 빠르게 구성하고, AWS에서 standalone 배포가 가능 |
| Backend | FastAPI | REST API + 비동기 LLM 호출·JSON 스키마 검증에 적합 |
| DB | SQLite | 관계형(Meeting 1:N ActionItem)을 유지하면서, 로컬·EC2 모두 설치 부담 없이 빠르게 굴리기 위함 |
| LLM | OpenRouter 무료 티어 | 과제 요건. 모델은 `.env`로 교체 가능 |
| 배포 | AWS (EC2 예정) | 과제 필수. 로컬 완주 후 배포 |

## 로컬 실행

### 1) Backend (SQLite는 별도 기동 불필요)

DB 파일은 첫 연결 시 `backend/data/meeting_action_tracker.db`에 생성될 예정입니다.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

헬스체크: http://localhost:8000/api/health

### 2) Frontend

```bash
cd frontend
# NEXT_PUBLIC_API_URL=http://localhost:8000 만 .env.local에 넣으면 됨
npm run dev
```

앱: http://localhost:3000

## AI(바이브코딩) 사용

- 초기 monorepo scaffold와 README 초안 작성에 Cursor를 사용했습니다.
- 이후에도 커밋 단위로 작업하며, 제출 시 각 커밋의 의도를 설명할 수 있게 유지합니다.
