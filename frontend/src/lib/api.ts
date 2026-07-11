/**
 * FastAPI 백엔드와 통신하는 클라이언트 헬퍼.
 *
 * 왜 파일로 분리하나?
 * - 페이지/컴포넌트마다 fetch URL을 하드코딩하지 않기 위해
 * - API 주소·에러 처리를 한곳에서 바꾸기 위해
 *
 * NEXT_PUBLIC_API_URL:
 * - Next.js에서 브라우저에도 노출되는 환경변수 (접두사 NEXT_PUBLIC_)
 * - 없으면 로컬 기본값 http://localhost:8000 사용
 *
 * 주의:
 * - 이 파일은 "호출"만 한다. DB/LLM 로직은 백엔드에 둔다.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

/** 백엔드가 떠 있는지 확인 (GET /api/health) */
export async function fetchHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/api/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}
