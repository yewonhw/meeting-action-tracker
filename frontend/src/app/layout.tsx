/**
 * 모든 페이지의 공통 껍데기 (App Router의 Root Layout).
 * - <html>/<body>, 메타데이터, 전역 CSS는 여기에 둔다.
 * - 개별 화면 내용은 children(각 page.tsx)으로 들어온다.
 */

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meeting Action Tracker",
  description: "회의록 액션아이템 관리 서비스",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
