/**
 * /meetings/new — 새 회의 입력 화면 (클라이언트)
 *
 * 사용자가 하는 일:
 * 1. 제목 입력
 * 2. 회의록 원문 붙여넣기
 * 3. (선택) "저장 후 AI 구조화" 체크
 * 4. 저장 버튼
 *
 * 코드가 하는 일:
 * 1. createMeeting API 호출 → 회의 생성
 * 2. 체크돼 있으면 startStructure API 호출 → AI 시작(바로 202)
 * 3. /meetings/{id} 상세 화면으로 이동
 */

"use client";

import { FormEvent, useState } from "react";
// useRouter = 코드로 페이지 이동할 때 사용
import { useRouter } from "next/navigation";
import { createMeeting, startStructure } from "@/lib/api";
import styles from "./new.module.css";

export default function NewMeetingPage() {
  const router = useRouter();

  // 입력칸과 연결된 상태 (controlled input)
  const [title, setTitle] = useState("");
  const [rawText, setRawText] = useState("");
  // true 면 저장 직후 AI 구조화도 시작
  const [runAi, setRunAi] = useState(true);
  // 저장 버튼 중복 클릭 방지
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * form 제출 이벤트 처리.
   * FormEvent = form 의 onSubmit 타입
   */
  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    // 브라우저 기본 동작(페이지 전체 새로고침)을 막음
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      // trim() = 앞뒤 공백 제거
      const meeting = await createMeeting({
        title: title.trim(),
        raw_text: rawText.trim(),
      });

      // AI 시작은 실패해도 "회의 자체"는 이미 만들어짐
      // → 그래도 상세로 보내고, 상세에서 다시 시도할 수 있게 함
      if (runAi) {
        try {
          await startStructure(meeting.id);
        } catch (err) {
          console.error(err);
        }
      }

      // 상세 페이지로 이동 (예: /meetings/12)
      router.push(`/meetings/${meeting.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장에 실패했습니다.");
      // 실패했을 때만 버튼을 다시 활성화
      setSubmitting(false);
    }
  }

  return (
    <main>
      <h1 className={styles.title}>새 회의</h1>
      <p className={`muted ${styles.lead}`}>
        회의록 원문을 붙여넣고 저장하세요. AI 구조화는 백그라운드에서 진행됩니다.
      </p>

      {/* onSubmit = 저장 버튼/Enter 로 폼이 제출될 때 */}
      <form className={styles.form} onSubmit={onSubmit}>
        <label className={styles.field}>
          <span>제목</span>
          {/*
            value + onChange = controlled component
            입력값이 항상 React state 와 같게 유지됨
          */}
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="예: 주간 제품 싱크"
            required
            maxLength={200}
          />
        </label>

        <label className={styles.field}>
          <span>회의록 원문</span>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="회의에서 나온 결정, 논의, 할 일을 그대로 붙여넣으세요."
            required
            rows={16}
          />
        </label>

        <label className={styles.check}>
          <input
            type="checkbox"
            checked={runAi}
            onChange={(e) => setRunAi(e.target.checked)}
          />
          <span>저장 후 AI 구조화 바로 시작</span>
        </label>

        {error ? <p className={styles.error}>{error}</p> : null}

        <div className={styles.actions}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => router.push("/")}
            disabled={submitting}
          >
            취소
          </button>
          {/* type="submit" = 이 버튼을 누르면 form onSubmit 실행 */}
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? "저장 중…" : "저장"}
          </button>
        </div>
      </form>
    </main>
  );
}
