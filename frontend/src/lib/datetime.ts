/**
 * API 가 준 ISO 시각 문자열을 한국 로컬 시각 글자로 바꾼다.
 *
 * 서버는 UTC 끝에 Z 를 붙여 보낸다 (예: 2026-07-12T04:56:54Z).
 * toLocaleString("ko-KR") 이 사용자 PC 시간대(한국이면 KST)로 바꿔 보여 준다.
 */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR");
}
