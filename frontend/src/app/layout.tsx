/**
 * Root Layout = 모든 페이지의 공통 뼈대.
 *
 * App Router 규칙:
 * - src/app/layout.tsx 는 필수에 가까운 공통 레이아웃
 * - 여기의 <html>, <body> 가 사이트 전체에 적용됨
 * - 각 page.tsx 내용은 {children} 자리에 들어감
 *
 * 예:
 *   layout 이 html/body 를 그리고
 *   page.tsx(Home) 가 body 안에 들어간다
 */

// Metadata = 브라우저 탭 제목, 검색/공유용 설명 등
// type import = 타입만 가져오고 실행 코드에는 안 넣음
import type { Metadata } from "next";

// 전역 CSS: 모든 페이지에 공통으로 적용되는 스타일
import "./globals.css";

/**
 * export const metadata
 * - Next.js가 이 값을 읽어서 <title>, <meta> 등을 만들어 줌
 * - 클라이언트에서 직접 쓰는 변수가 아니라 프레임워크용 설정
 */
export const metadata: Metadata = {
  title: "Meeting Action Tracker", // 브라우저 탭에 보이는 제목
  description: "회의록 액션아이템 관리 서비스", // 페이지 설명
};

/**
 * RootLayout 컴포넌트
 *
 * @param children - 하위 페이지(예: page.tsx)가 여기에 렌더링됨
 * Readonly<...> - props 객체를 읽기 전용으로 취급하겠다는 타입 표시
 * React.ReactNode - 화면에 그릴 수 있는 것(문자, 태그, 컴포넌트 등)
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // lang="ko" = 이 문서의 주 언어가 한국어임을 브라우저/접근성 도구에 알림
    <html lang="ko">
      {/* body 안에 실제 페이지 내용이 들어간다 */}
      <body>{children}</body>
    </html>
  );
}
