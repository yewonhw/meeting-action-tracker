/**
 * page.tsx (홈 /) — 서버 컴포넌트
 *
 * 왜 HomeClient 로 나누나?
 * - 목록을 불러오려면 useEffect / useState 가 필요하다
 * - 그 훅들은 브라우저(클라이언트)에서만 동작한다
 * - page.tsx 전체를 "use client" 로 두면 Next.js 일부 버전에서
 *   Manifest 오류가 나서, 서버 page 는 얇게 두고
 *   실제 UI만 HomeClient 로 분리했다
 */

import HomeClient from "./HomeClient";

export default function HomePage() {
  // 서버는 HomeClient 를 그리라고만 지시
  return <HomeClient />;
}
