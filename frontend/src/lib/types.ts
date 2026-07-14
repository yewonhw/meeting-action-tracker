/**
 * types.ts — 데이터 "모양"만 적어 둔 파일
 *
 * TypeScript 의 type 은 실행 때 사라진다.
 * 대신 코딩할 때 "이 객체에 어떤 칸이 있어야 하는지" 를 알려 줘서
 * 오타·빠진 필드를 미리 잡아 준다.
 *
 * 백엔드 FastAPI 스키마(meeting.py)와 이름을 맞춰 두었다.
 * 프론트는 이 타입을 보고, 백엔드는 Pydantic 으로 같은 필드를 검사한다.
 */

/**
 * AI 구조화가 어디쯤인지.
 * | 값이면 그 글자들만 쓸 수 있다. (다른 글자를 쓰면 타입 에러)
 */
export type AiStatus = "pending" | "processing" | "done" | "failed";

/** 할 일이 끝났는지 */
export type ActionStatus = "todo" | "done";

/**
 * 목록 화면용 회의 정보.
 * 원문·액션 목록은 안 넣어서 가볍게 받는다. (GET /api/meetings)
 */
export type MeetingListItem = {
  id: number; // 회의 고유 번호
  title: string; // 제목
  // 백엔드가 새 상태를 추가해도 깨지지 않게 string 도 허용
  ai_status: AiStatus | string;
  created_at: string; // ISO 날짜 문자열. 예: 2026-07-12T04:00:00
  updated_at: string;
};

/**
 * 할 일 1개. (GET 상세의 action_items[] 한 칸)
 */
export type ActionItem = {
  id: number;
  meeting_id: number; // 어느 회의 소속인지
  task: string; // 할 일 내용
  assignee: string | null; // 담당자. 없으면 null
  due_date: string | null; // 기한 YYYY-MM-DD. 없으면 null
  status: ActionStatus | string;
  created_at: string;
  updated_at: string;
};

/**
 * 회의 상세 전체.
 * decisions / discussions 는 배열이 아니라 JSON 문자열이다.
 * 예: '["배포 보류","토큰 7일"]'
 * 화면에서 쓰려면 api.ts 의 parseJsonStringList 로 풀어야 한다.
 */
export type Meeting = {
  id: number;
  title: string;
  raw_text: string; // 사용자가 붙여넣은 원문
  decisions: string | null;
  discussions: string | null;
  ai_status: AiStatus | string;
  ai_error: string | null; // 실패했을 때만 이유 글자
  created_at: string;
  updated_at: string;
  action_items: ActionItem[];
};

/** POST /api/meetings 에 보낼 본문 */
export type MeetingCreatePayload = {
  title: string;
  raw_text: string;
};

/**
 * PATCH /api/meetings/{id} 에 보낼 본문.
 * ? 가 붙은 칸은 "안 보내도 됨" = 부분 수정.
 */
export type MeetingUpdatePayload = {
  title?: string;
  raw_text?: string;
  decisions?: string | null;
  discussions?: string | null;
};

/** PATCH /api/action-items/{id} 에 보낼 본문 */
export type ActionItemUpdatePayload = {
  task?: string;
  assignee?: string | null;
  due_date?: string | null;
  status?: ActionStatus;
};

/** GET /api/action-items 목록 한 줄 (회의 제목 포함) */
export type ActionItemListItem = {
  id: number;
  meeting_id: number;
  /** 서버가 Meeting 과 join 해서 채워 줌. 보드에서 소속 회의 표시용 */
  meeting_title: string;
  task: string;
  assignee: string | null;
  due_date: string | null;
  status: ActionStatus | string;
  created_at: string;
  updated_at: string;
};

/** 백엔드 ActionSortBy 와 동일. 임의 문자열로 정렬 컬럼을 열지 않기 위함 */
export type ActionSortBy = "due_date" | "assignee" | "status" | "created_at";
export type SortDir = "asc" | "desc";

/**
 * listActionItems() 에 넘기는 쿼리.
 * 필드가 곧 ?assignee=&status=&due_to=... 가 된다.
 * 프론트에서 받은 뒤 다시 filter 하지 말고, 필요하면 여기 값을 바꿔 재요청한다.
 *
 * due_to: 이 날짜까지(이하). 보통 오늘을 넣어 "오늘까지·지난 기한"을 본다.
 */
export type ActionItemListParams = {
  assignee?: string;
  status?: ActionStatus;
  due_to?: string;
  sort_by?: ActionSortBy;
  sort_dir?: SortDir;
};
