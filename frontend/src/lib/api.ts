/**
 * api.ts — 브라우저가 백엔드(FastAPI)에게 HTTP 요청을 보내는 함수 모음
 *
 * 화면(page)은 이 파일만 부르고, URL을 직접 적지 않는다.
 * 나중에 주소가 바뀌면 여기만 고치면 된다.
 *
 * NEXT_PUBLIC_API_URL:
 * - Next.js 규칙: NEXT_PUBLIC_ 으로 시작해야 브라우저 코드에서 읽힌다
 * - frontend/.env.local 에 적으면 됨
 * - 없으면 기본값 http://localhost:8000 (로컬 백엔드)
 */

import type {
  ActionItem,
  ActionItemUpdatePayload,
  Meeting,
  MeetingCreatePayload,
  MeetingListItem,
  MeetingUpdatePayload,
} from "./types";

// ?? = 왼쪽이 null/undefined 일 때만 오른쪽 사용
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** 다른 곳에서 base URL 이 필요할 때 */
export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/**
 * 모든 API 호출의 공통 엔진.
 *
 * T = 성공했을 때 돌아올 데이터 타입 (호출할 때 정해짐)
 * path = "/api/meetings" 처럼 base 뒤에 붙는 경로
 * options = method, body 등 fetch 옵션
 */
async function requestJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  // Headers 객체로 복사해서 Content-Type 을 안전하게 추가
  const headers = new Headers(options.headers);

  // body 가 있으면 "이건 JSON 이에요" 라고 서버에 알려야 함
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  // 실제 네트워크 요청
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options, // method, body 등을 그대로 전달
    headers,
  });

  // 204 No Content = 성공인데 본문 없음 (삭제 API)
  if (response.status === 204) {
    return null as T;
  }

  // 본문을 글자로 읽고, 가능하면 JSON 객체로 변환
  const raw = await response.text();
  let data: unknown = null;
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      // JSON 이 아니면 글자 그대로 보관
      data = raw;
    }
  }

  // 200~299 가 아니면 실패 → Error 를 던져서 화면 catch 로 감
  if (!response.ok) {
    // FastAPI 에러 형식: { "detail": "Meeting not found" }
    const detail =
      typeof data === "object" &&
      data !== null &&
      "detail" in data &&
      typeof (data as { detail: unknown }).detail === "string"
        ? (data as { detail: string }).detail
        : `Request failed: ${response.status}`;
    throw new Error(detail);
  }

  // 성공: 파싱한 데이터를 T 타입으로 돌려줌
  return data as T;
}

/** 백엔드가 켜져 있는지 확인 (GET /api/health) */
export async function fetchHealth(): Promise<{ status: string }> {
  return requestJson("/api/health");
}

/** 회의 목록 (가벼운 필드만) */
export async function listMeetings(): Promise<MeetingListItem[]> {
  return requestJson("/api/meetings");
}

/**
 * 회의 1건 상세.
 * AI가 processing 중일 때 상세 화면이 이 함수를 반복 호출한다 (= 폴링).
 */
export async function getMeeting(id: number): Promise<Meeting> {
  // 템플릿 문자열로 경로에 id 끼워 넣기
  return requestJson(`/api/meetings/${id}`);
}

/** 새 회의 만들기. body 는 JS 객체 → JSON 글자로 변환해서 보냄 */
export async function createMeeting(
  payload: MeetingCreatePayload,
): Promise<Meeting> {
  return requestJson("/api/meetings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** 회의 일부 수정 (결정/논의 검토 저장 등) */
export async function updateMeeting(
  id: number,
  payload: MeetingUpdatePayload,
): Promise<Meeting> {
  return requestJson(`/api/meetings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/** 회의 삭제. 성공하면 본문 없음 */
export async function deleteMeeting(id: number): Promise<void> {
  await requestJson<null>(`/api/meetings/${id}`, { method: "DELETE" });
}

/**
 * AI 구조화 시작.
 * 서버는 바로 202 + ai_status=processing 을 준다.
 * 진짜 결과는 나중에 getMeeting 으로 확인한다.
 */
export async function startStructure(id: number): Promise<Meeting> {
  return requestJson(`/api/meetings/${id}/structure`, {
    method: "POST",
  });
}

/** 액션 1개 수정. 예: status 를 done 으로 */
export async function updateActionItem(
  id: number,
  payload: ActionItemUpdatePayload,
): Promise<ActionItem> {
  return requestJson(`/api/action-items/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/**
 * DB에 저장된 JSON 글자 배열을 JS 배열로 푼다.
 *
 * 입력 예: '["배포 보류","토큰 7일"]'
 * 출력 예: ["배포 보류", "토큰 7일"]
 *
 * null 이거나 깨진 JSON 이면 [] (빈 목록)을 줘서 화면이 안 죽게 함.
 */
export function parseJsonStringList(value: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value) as unknown;
    // 배열이 아니면 무시
    if (!Array.isArray(parsed)) return [];
    // 글자만 남기기 (숫자 등이 섞여 있으면 제외)
    return parsed.filter((item): item is string => typeof item === "string");
  } catch {
    return [];
  }
}
