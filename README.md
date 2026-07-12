# Meeting Action Tracker

회의록 텍스트를 AI로 구조화하고, 결정사항·액션아이템·논의사항을 관리하는 웹 서비스입니다.

## 데모

- **배포 URL**: http://54.180.86.56
- **GitHub**: https://github.com/yewonhw/meeting-action-tracker

> EC2 공인 IP는 인스턴스를 재시작하면 바뀔 수 있습니다.

## 현재 상태

### 된 것

- Frontend(Next.js) / Backend(FastAPI) monorepo, REST로 분리
- 관계형 모델: Meeting 1:N ActionItem (SQLite)
- Meeting / ActionItem CRUD + AI 결과 검토·수정(결정/논의·액션 할일/담당자/기한 편집·삭제)
- OpenRouter 무료 모델로 회의록 구조화 + JSON 스키마 검증
- 환각 방지: 프롬프트 제약 + 저장 전 원문 근거 검사(담당자·기한)
- AI 비동기 처리: `202 Accepted` → 백그라운드 실행, `ai_status` 폴링, 타임아웃/`failed`
- AWS EC2 + nginx 배포 (`/` → Next.js, `/api` → FastAPI)

### 일부러 미룬 것 / 약한 부분

- **전역 액션 보드**: 액션은 회의 상세 안에서 목록·완료 처리. 회의를 가로지르는 통합 할 일 화면은 없음
- **액션 수동 추가 UI**: 액션 생성은 AI 구조화(또는 API) 중심. 화면에서는 기존 액션 수정·삭제·완료 토글
- **결정/논의 문장 단위 원문 검증**: 담당자·기한만 자동 null 처리. 문장 hallucination은 사용자가 상세 화면에서 고치도록 함
- **RDS/HTTPS/도메인**: MVP는 EC2 단일 인스턴스 + SQLite + HTTP(IP). 운영 hardening은 범위 밖

## 아키텍처

```
Browser
  → nginx :80
       /      → Next.js :3000
       /api   → FastAPI :8000 → SQLite 파일
                              → OpenRouter (LLM)
```

로컬에서는 프론트가 `NEXT_PUBLIC_API_URL=http://localhost:8000` 으로 백엔드를 직접 호출합니다.
배포에서는 같은 호스트의 `/api` 로 프록시하므로 빌드 시 `NEXT_PUBLIC_API_URL` 을 비워 둡니다.

## 데이터 모델

```
meetings                         action_items
─────────                        ────────────
id (PK)                          id (PK)
title                            meeting_id (FK → meetings.id)
raw_text                         task
decisions (nullable)             assignee (nullable)  ← 원문에 없으면 null
discussions (nullable)           due_date (nullable) ← 원문 근거 없으면 null
ai_status                        status (todo|done)
ai_error                         created_at / updated_at
created_at / updated_at

Meeting 1 ──────── < ActionItem N
```

- 회의 삭제 시 소속 액션아이템도 함께 삭제 (ORM cascade + FK ON DELETE CASCADE)

## 환각(hallucination) 방지

1. **프롬프트**: 원문에 있는 내용만 추출, 오늘 날짜 제공, 모호한 기한은 null
2. **JSON 스키마(Pydantic)**: 형식 강제. `"null"` 문자열·`"금요일"` 같은 비날짜는 null로 정규화
3. **원문 근거 검사(저장 직전)**: `assignee`가 원문에 없으면 null, `due_date`가 원문 표기(예: `7월 15일`, ISO)와 맞지 않으면 null

관련 코드: `backend/app/services/hallucination.py`, `structure.py`, `openrouter.py`

## 스택 선택 이유

| 영역 | 선택 | 이유 |
| ---- | ---- | ---- |
| Frontend | Next.js (App Router) | React UI·라우팅, EC2에서 `next start`로 배포 가능 |
| Backend | FastAPI | REST + 백그라운드 AI 호출 + JSON 검증 |
| DB | SQLite | 관계형 유지, 로컬·EC2 모두 설치 부담 없음 |
| LLM | OpenRouter 무료 티어 | 과제 요건. 모델은 `.env`로 교체 |
| 배포 | AWS EC2 + nginx | 단일 인스턴스로 FE/BE 프록시 |

## 로컬 실행

루트 `.env` 예시는 `.env.example` 참고. `OPENROUTER_API_KEY` 필요.

### 1) Backend

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
# frontend/.env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

앱: http://localhost:3000

## AWS 배포 요약

- AMI: Amazon Linux 2023
- 프로세스: systemd `mat-api`(uvicorn), `mat-web`(next start)
- 리버스 프록시: nginx `/` → :3000, `/api` → :8000
- 시크릿: 서버 `~/meeting-action-tracker/.env` (git에 없음)
- 보안 그룹: 22(SSH, 내 IP), 80(HTTP)

## 우선순위 / 판단

1. 관계형 모델 → CRUD API → AI JSON 구조화 → 비동기·폴링 → 프론트 플로우 → EC2 배포
2. 배포를 환각 하드 검증보다 먼저 끝낸 뒤, 제출 직전 원문 근거 검사를 보강
3. 화려한 UI·RDS·도메인보다 “끝까지 돌아가는 필수 플로우”를 우선

## AI(바이브코딩) 사용

- Cursor로 scaffold, 기능 구현, 배포 스크립트 작성을 도움받음
- 커밋은 작업 단위로 분리해 두었고, 제출 시 각 커밋의 의도를 설명할 수 있게 유지함
