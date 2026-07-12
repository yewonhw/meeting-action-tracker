/**
 * FastAPI 백엔드와 통신하는 클라이언트 헬퍼.
 *
 * 왜 파일로 분리하나?
 * - 페이지마다 fetch URL을 하드코딩하지 않기 위해
 * - API 주소·에러 처리를 한곳에서 바꾸기 위해
 *
 * NEXT_PUBLIC_API_URL:
 * - Next.js에서 브라우저에도 노출되는 환경변수 (접두사 NEXT_PUBLIC_ 필요)
 * - frontend/.env.local 에 넣으면 됨
 * - 없으면 로컬 기본값 http://localhost:8000 사용
 *
 * 주의:
 * - 이 파일은 HTTP 호출만 한다
 * - DB 저장, AI 호출 같은 본업 로직은 백엔드(FastAPI)에 있다
 */

/**
 * API 서버 기본 주소
 * process.env.XXX = 환경변수 읽기
 * ?? = 왼쪽이 null/undefined 일 때만 오른쪽 기본값 사용
 */
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * 다른 파일에서 기본 주소를 알고 싶을 때 쓰는 getter
 * (지금은 단순 반환, 나중에 로그/검증을 넣기 쉬움)
 */
export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/**
 * 백엔드가 살아 있는지 확인한다.
 * 요청: GET {API_BASE_URL}/api/health
 * 성공 예: { "status": "ok" }
 *
 * async = 네트워크 응답을 기다리는 함수
 * Promise<...> = 나중에 { status: string } 형태 결과가 온다는 뜻
 */
export async function fetchHealth(): Promise<{ status: string }> {
  // fetch = 브라우저/Node 가 제공하는 HTTP 요청 함수
  const response = await fetch(`${API_BASE_URL}/api/health`);

  // response.ok = 상태코드가 200~299 범위인지
  if (!response.ok) {
    // 실패하면 에러를 던져서 호출한 쪽에서 처리하게 함
    throw new Error(`Health check failed: ${response.status}`);
  }

  // response.json() = 응답 본문을 JS 객체로 파싱
  return response.json();
}
