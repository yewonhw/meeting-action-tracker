/**
 * HomeClient.tsx — 홈 화면의 실제 UI (브라우저에서 실행)
 *
 * "use client" 가 맨 위에 있어야
 * useState, useEffect 같은 브라우저 전용 기능을 쓸 수 있다.
 *
 * 흐름:
 * 1. 처음 화면이 열리면 meetings = null (로딩)
 * 2. useEffect 가 listMeetings() 호출
 * 3. 성공하면 목록 표시 / 실패하면 error 메시지
 */

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listMeetings } from "@/lib/api";
import type { MeetingListItem } from "@/lib/types";
// CSS Modules: 이 파일 전용 클래스. styles.title 처럼 씀
import styles from "./page.module.css";

/** 백엔드 ai_status → CSS 클래스 이름 */
function statusClass(status: string): string {
  switch (status) {
    case "processing":
      return "status status-processing";
    case "done":
      return "status status-done";
    case "failed":
      return "status status-failed";
    default:
      return "status status-pending";
  }
}

/** 백엔드 ai_status → 화면에 보일 한글 */
function statusLabel(status: string): string {
  switch (status) {
    case "processing":
      return "구조화 중";
    case "done":
      return "완료";
    case "failed":
      return "실패";
    default:
      return "대기";
  }
}

export default function HomeClient() {
  /**
   * useState = 값이 바뀌면 화면을 다시 그린다
   * meetings:
   *   null  → 아직 서버 응답 전
   *   []    → 응답은 왔는데 회의 0개
   *   [...] → 회의 목록
   */
  const [meetings, setMeetings] = useState<MeetingListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * useEffect = "화면이 나타난 뒤" 한 번(또는 의존성 변경 시) 실행
   * [] = 의존성 없음 → 처음 마운트될 때 1번만
   */
  useEffect(() => {
    // 컴포넌트가 사라진 뒤에 setState 하면 경고가 나므로 깃발로 막음
    let cancelled = false;

    async function load() {
      try {
        const data = await listMeetings();
        if (!cancelled) {
          setMeetings(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          // Error 객체면 message, 아니면 기본 문구
          setError(
            err instanceof Error ? err.message : "목록을 불러오지 못했습니다.",
          );
          setMeetings([]);
        }
      }
    }

    // async 함수를 바로 실행 (반환 Promise 는 무시)
    void load();

    // cleanup: 페이지를 떠나면 cancelled = true
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main>
      <div className={styles.hero}>
        <h1 className={styles.title}>회의록을 구조화하고 액션을 추적합니다</h1>
        <p className={`muted ${styles.lead}`}>
          원문을 붙이면 AI가 결정·논의·할 일을 나누고, 여기서 검토·수정할 수 있습니다.
        </p>
      </div>

      <section className={styles.section}>
        <div className={styles.sectionHead}>
          <h2>회의 목록</h2>
          <Link href="/meetings/new" className="btn btn-secondary">
            새로 만들기
          </Link>
        </div>

        {/* 조건부 렌더: 조건이 참일 때만 그 태그 표시 */}
        {error ? <p className={styles.error}>{error}</p> : null}
        {meetings === null ? <p className="muted">불러오는 중…</p> : null}
        {meetings && meetings.length === 0 && !error ? (
          <p className="muted">아직 회의가 없습니다. 새 회의를 만들어 보세요.</p>
        ) : null}

        {meetings && meetings.length > 0 ? (
          <ul className={styles.list}>
            {/* map = 배열 각 항목을 <li> 로 변환. key 는 React 가 목록을 구분하는 ID */}
            {meetings.map((meeting) => (
              <li key={meeting.id}>
                <Link href={`/meetings/${meeting.id}`} className={styles.row}>
                  <div>
                    <div className={styles.rowTitle}>{meeting.title}</div>
                    <div className={`muted ${styles.rowMeta}`}>
                      #{meeting.id} ·{" "}
                      {new Date(meeting.created_at).toLocaleString("ko-KR")}
                    </div>
                  </div>
                  <span className={statusClass(meeting.ai_status)}>
                    {statusLabel(meeting.ai_status)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </main>
  );
}
