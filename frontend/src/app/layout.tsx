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
