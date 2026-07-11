# Meeting Action Tracker

회의록 텍스트를 AI로 구조화하고, 결정사항·액션아이템·논의사항을 관리하는 웹 서비스입니다.

## 현재 상태

### 된 것
- Frontend(Next.js) / Backend(FastAPI) monorepo 뼈대
- Backend `GET /api/health` 헬스체크
- 로컬 PostgreSQL용 `docker-compose.yml`
- 환경변수 예시 (`.env.example`)

### 아직 안 된 것
- 관계형 데이터 모델 (Meeting 1:N ActionItem)
- AI 구조화 (OpenRouter)
- CRUD / 비동기 AI 처리
- 실제 화면 플로우
- AWS 배포

## 아키텍처 (예정)

```
Browser → Next.js (frontend)
                │ HTTP
                ▼
         FastAPI (backend) → PostgreSQL
                │
                ▼
           OpenRouter (LLM)
```

배포 시 EC2 + nginx로 `/` → Next, `/api` → FastAPI 연결 예정.

## 스택 선택 이유

| 영역 | 선택 | 이유 |
|------|------|------|
| Frontend | Next.js (App Router) | React 기반 UI·라우팅을 빠르게 구성하고, AWS에서 standalone 배포가 가능 |
| Backend | FastAPI | REST API + 비동기 LLM 호출·JSON 스키마 검증에 적합 |
| DB | PostgreSQL | Meeting 1:N ActionItem 관계 모델링, 이후 RDS 이관이 수월 |
| LLM | OpenRouter 무료 티어 | 과제 요건. 모델은 `.env`로 교체 가능 |
| 배포 | AWS (EC2 예정) | 과제 필수. 로컬 완주 후 배포 |

## 로컬 실행

### 1) DB

```bash
docker compose up -d
```

### 2) Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

헬스체크: http://localhost:8000/api/health

### 3) Frontend

```bash
cd frontend
cp ../.env.example .env.local   # 필요 시 NEXT_PUBLIC_API_URL만 남기고 수정
npm run dev
```

앱: http://localhost:3000

## 앞으로의 커밋 계획

1. DB 모델 + 마이그레이션 (Meeting 1:N ActionItem)
2. Meeting / ActionItem CRUD API
3. OpenRouter 구조화 + JSON 강제·검증
4. AI 비동기 상태 처리 (loading / fail / timeout)
5. Next.js 입력·검토·수정 UI
6. 액션아이템 목록
7. AWS 배포
8. (여유) 필터·대시보드·로그인

## AI(바이브코딩) 사용

- 초기 monorepo scaffold와 README 초안 작성에 Cursor를 사용했습니다.
- 이후에도 커밋 단위로 작업하며, 제출 시 각 커밋의 의도를 설명할 수 있게 유지합니다.
