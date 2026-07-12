/**
 * layout.tsx — 모든 페이지에 공통으로 씌우는 뼈대
 *
 * Next.js App Router 규칙:
 * - src/app/layout.tsx 는 사이트 전체의 html/body 를 담당
 * - 각 페이지(page.tsx) 내용은 아래 {children} 자리에 들어간다
 *
 * 그래서 헤더(로고, 새 회의 버튼)를 여기 두면
 * 목록/생성/상세 어디서든 같은 상단이 보인다.
 */

import type { Metadata } from "next";
// Link = <a> 대신 쓰는 Next.js 이동 컴포넌트 (페이지 전체 새로고침을 줄임)
import Link from "next/link";
// 전역 CSS (버튼, 색 변수 등)
import "./globals.css";

/**
 * metadata = 브라우저 탭 제목, 검색용 설명.
 * 이 객체는 화면에 직접 안 그려지고, Next.js 가 <head> 에 넣어 준다.
 */
export const metadata: Metadata = {
  title: "Meeting Action Tracker",
  description: "회의록 액션아이템 관리 서비스",
};

/**
 * RootLayout
 * @param children - 지금 열려 있는 페이지의 UI
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // lang="ko" = 문서 언어가 한국어
    <html lang="ko">
      <body>
        {/* shell = 가운데 정렬된 컨텐츠 폭 (globals.css) */}
        <div className="shell">
          <header className="site-header">
            {/* 클릭하면 홈(/)으로 */}
            <Link href="/" className="brand">
              Meeting Action Tracker
            </Link>
            <div className="header-actions">
              {/* 클릭하면 새 회의 입력 화면으로 */}
              <Link href="/meetings/new" className="btn btn-primary">
                새 회의
              </Link>
            </div>
          </header>

          {/* 여기 아래에 page.tsx 내용이 렌더링됨 */}
          {children}
        </div>
      </body>
    </html>
  );
}
