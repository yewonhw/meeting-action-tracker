/**
 * /meetings/[id] — 회의 상세 화면 (클라이언트)
 *
 * [id] = URL 에 들어가는 동적 값. 예: /meetings/9 → id = "9"
 *
 * 화면이 하는 일 (위에서 아래):
 * 1. URL 에서 회의 id 읽기
 * 2. GET 으로 회의 불러오기
 * 3. ai_status === "processing" 이면 1.5초마다 다시 GET (폴링)
 * 4. 원문 / 결정·논의 편집 / 액션 검토·수정·삭제
 * 5. 버튼: AI 시작·재시도, 회의 삭제
 */

"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deleteActionItem,
  deleteMeeting,
  getMeeting,
  parseJsonStringList,
  startStructure,
  updateActionItem,
  updateMeeting,
} from "@/lib/api";
import type { ActionItem, Meeting } from "@/lib/types";
import styles from "./detail.module.css";

/** 폴링 간격 (밀리초). 1500 = 1.5초 */
const POLL_MS = 1500;

/**
 * 액션 1개를 화면에서 고치기 위한 임시 입력값.
 * 서버 값과 따로 두었다가 "액션 저장" 을 누를 때 PATCH 로 보낸다.
 */
type ActionDraft = {
  task: string;
  assignee: string;
  due_date: string;
};

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

/** 서버 ActionItem → 입력칸용 draft */
function toDraft(item: ActionItem): ActionDraft {
  return {
    task: item.task,
    // null 이면 빈 칸으로 보여 줌
    assignee: item.assignee ?? "",
    due_date: item.due_date ?? "",
  };
}

export default function MeetingDetailPage() {
  // useParams = URL 동적 구간 읽기. id 는 문자열로 옴
  const params = useParams<{ id: string }>();
  const router = useRouter();
  // 숫자로 바꿔 API 에 넘김
  const meetingId = Number(params.id);

  // 서버에서 받은 회의 전체. null = 아직 로딩
  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 버튼 연속 클릭 막기
  const [busy, setBusy] = useState(false);

  /**
   * 결정/논의 편집용 텍스트.
   * 서버는 JSON 문자열로 저장하지만,
   * 사람은 textarea 에서 한 줄에 하나 쓰는 게 편해서 줄바꿈 텍스트로 보관.
   */
  const [decisionsText, setDecisionsText] = useState("");
  const [discussionsText, setDiscussionsText] = useState("");

  /**
   * 액션별 입력 임시값.
   * key = action_item.id
   * 서버에서 목록을 다시 받으면 이 객체도 같이 맞춰 준다.
   */
  const [actionDrafts, setActionDrafts] = useState<Record<number, ActionDraft>>(
    {},
  );

  /** 서버 회의 데이터로 화면 state 를 맞춘다 */
  function applyMeeting(data: Meeting) {
    setMeeting(data);
    setDecisionsText(parseJsonStringList(data.decisions).join("\n"));
    setDiscussionsText(parseJsonStringList(data.discussions).join("\n"));
    // 액션 draft 를 서버 값으로 다시 채움
    const next: Record<number, ActionDraft> = {};
    for (const item of data.action_items) {
      next[item.id] = toDraft(item);
    }
    setActionDrafts(next);
  }

  /**
   * useCallback = 함수를 기억해 두고, meetingId 가 바뀔 때만 새로 만듦
   * (폴링 useEffect 의존성에 넣기 좋게)
   */
  const refresh = useCallback(async () => {
    const data = await getMeeting(meetingId);
    applyMeeting(data);
    return data;
  }, [meetingId]);

  // --- 첫 로딩 ---
  useEffect(() => {
    // id 가 숫자가 아니면 바로 에러
    if (!Number.isFinite(meetingId)) {
      setError("잘못된 회의 ID 입니다.");
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const data = await getMeeting(meetingId);
        if (!cancelled) {
          applyMeeting(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "불러오기 실패");
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [meetingId]);

  // --- 폴링: processing 인 동안만 타이머 동작 ---
  useEffect(() => {
    // 조건이 아니면 타이머를 안 만듦
    if (!meeting || meeting.ai_status !== "processing") return;

    // setInterval = POLL_MS 마다 함수 반복 실행
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          await refresh(); // 안에서 ai_status 가 done/failed 로 바뀌면
          // 다음 렌더에서 이 effect 가 정리되어 타이머가 멈춤
        } catch (err) {
          setError(err instanceof Error ? err.message : "상태 확인 실패");
        }
      })();
    }, POLL_MS);

    // cleanup: 언마운트 또는 의존성 변경 시 타이머 제거 (메모리 누수 방지)
    return () => window.clearInterval(timer);
  }, [meeting, refresh]);

  // meeting.action_items 가 없으면 빈 배열
  const actionItems = useMemo(
    () => meeting?.action_items ?? [],
    [meeting?.action_items],
  );

  /** draft 한 칸만 바꾸기 */
  function patchDraft(
    id: number,
    field: keyof ActionDraft,
    value: string,
  ) {
    setActionDrafts((prev) => ({
      ...prev,
      [id]: {
        ...(prev[id] ?? { task: "", assignee: "", due_date: "" }),
        [field]: value,
      },
    }));
  }

  /** AI 구조화 시작/재시도 버튼 */
  async function onStartStructure() {
    setBusy(true);
    setError(null);
    try {
      const updated = await startStructure(meetingId);
      // 보통 ai_status=processing → 위 폴링 effect 가 자동으로 돌아감
      applyMeeting(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "구조화 시작 실패");
    } finally {
      setBusy(false);
    }
  }

  /** 결정/논의 textarea 내용을 서버에 저장 */
  async function onSaveReview() {
    setBusy(true);
    setError(null);
    try {
      // 줄 단위로 자르고, 빈 줄 제거
      const decisions = decisionsText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      const discussions = discussionsText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);

      // 백엔드는 JSON 문자열을 기대하므로 stringify
      const updated = await updateMeeting(meetingId, {
        decisions: JSON.stringify(decisions),
        discussions: JSON.stringify(discussions),
      });
      applyMeeting(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "저장 실패");
    } finally {
      setBusy(false);
    }
  }

  /** 체크박스: todo ↔ done 토글 */
  async function onToggleAction(id: number, current: string) {
    const next = current === "done" ? "todo" : "done";
    try {
      await updateActionItem(id, { status: next });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "액션 상태 수정 실패");
    }
  }

  /**
   * 액션 1개의 할 일·담당자·기한을 서버에 저장.
   * 빈 담당자/기한은 null 로 보내서 "없음"으로 저장한다.
   */
  async function onSaveAction(id: number) {
    const draft = actionDrafts[id];
    if (!draft) return;

    const task = draft.task.trim();
    if (!task) {
      setError("할 일 내용은 비울 수 없습니다.");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await updateActionItem(id, {
        task,
        assignee: draft.assignee.trim() || null,
        // type="date" 값이 비어 있으면 null
        due_date: draft.due_date.trim() || null,
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "액션 저장 실패");
    } finally {
      setBusy(false);
    }
  }

  /** 액션 1개만 삭제 (회의는 유지) */
  async function onDeleteAction(id: number) {
    if (!window.confirm("이 액션아이템을 삭제할까요?")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteActionItem(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "액션 삭제 실패");
    } finally {
      setBusy(false);
    }
  }

  /** 회의 삭제 후 목록으로 */
  async function onDelete() {
    if (!window.confirm("이 회의를 삭제할까요? 액션아이템도 함께 삭제됩니다.")) {
      return;
    }
    setBusy(true);
    try {
      await deleteMeeting(meetingId);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "삭제 실패");
      setBusy(false);
    }
  }

  // --- 로딩/에러 초기 화면 ---
  if (error && !meeting) {
    return (
      <main>
        <p className={styles.error}>{error}</p>
        <Link href="/" className="btn btn-secondary">
          목록으로
        </Link>
      </main>
    );
  }

  if (!meeting) {
    return (
      <main>
        <p className="muted">불러오는 중…</p>
      </main>
    );
  }

  // processing 중이거나 다른 작업 중이면 편집 버튼 비활성
  const canStartAi = meeting.ai_status !== "processing" && !busy;
  const editingLocked = busy || meeting.ai_status === "processing";

  return (
    <main className={styles.wrap}>
      <div className={styles.top}>
        <div>
          <p className={`muted ${styles.back}`}>
            <Link href="/">← 목록</Link>
          </p>
          <h1 className={styles.title}>{meeting.title}</h1>
          <div className={styles.meta}>
            <span className={statusClass(meeting.ai_status)}>
              {statusLabel(meeting.ai_status)}
            </span>
            <span className="muted">
              #{meeting.id} · {new Date(meeting.created_at).toLocaleString("ko-KR")}
            </span>
          </div>
        </div>

        <div className={styles.topActions}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void onStartStructure()}
            disabled={!canStartAi}
          >
            {meeting.ai_status === "processing"
              ? "구조화 중…"
              : meeting.ai_status === "done" || meeting.ai_status === "failed"
                ? "다시 구조화"
                : "AI 구조화 시작"}
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => void onDelete()}
            disabled={editingLocked}
          >
            삭제
          </button>
        </div>
      </div>

      {error ? <p className={styles.error}>{error}</p> : null}

      {meeting.ai_status === "processing" ? (
        <p className={styles.bannerWarn}>
          AI가 회의록을 나누는 중입니다. 잠시만 기다려 주세요.
        </p>
      ) : null}

      {meeting.ai_status === "failed" ? (
        <p className={styles.bannerDanger}>
          {/* ?? = 왼쪽이 null/undefined 이면 오른쪽 */}
          구조화 실패: {meeting.ai_error ?? "알 수 없는 오류"}
        </p>
      ) : null}

      <section className={styles.panel}>
        <h2>원문</h2>
        {/* pre = 줄바꿈·공백을 그대로 보여줌 */}
        <pre className={styles.raw}>{meeting.raw_text}</pre>
      </section>

      <section className={styles.panel}>
        <div className={styles.panelHead}>
          <h2>결정 / 논의 (검토·수정)</h2>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void onSaveReview()}
            disabled={editingLocked}
          >
            수정 저장
          </button>
        </div>
        <p className={`muted ${styles.hint}`}>한 줄에 항목 하나씩 적으세요.</p>
        <div className={styles.grid2}>
          <label className={styles.field}>
            <span>결정사항</span>
            <textarea
              value={decisionsText}
              onChange={(e) => setDecisionsText(e.target.value)}
              rows={6}
              disabled={editingLocked}
            />
          </label>
          <label className={styles.field}>
            <span>논의사항</span>
            <textarea
              value={discussionsText}
              onChange={(e) => setDiscussionsText(e.target.value)}
              rows={6}
              disabled={editingLocked}
            />
          </label>
        </div>
      </section>

      <section className={styles.panel}>
        <h2>액션아이템 (검토·수정)</h2>
        <p className={`muted ${styles.hint}`}>
          AI 결과를 그대로 두지 말고, 할 일·담당자·기한을 확인한 뒤 저장하세요.
        </p>
        {actionItems.length === 0 ? (
          <p className="muted">아직 액션이 없습니다. AI 구조화를 실행해 보세요.</p>
        ) : (
          <ul className={styles.actions}>
            {actionItems.map((item) => {
              // draft 가 아직 없으면 서버 값으로 채운 기본값 사용
              const draft = actionDrafts[item.id] ?? toDraft(item);
              return (
                <li key={item.id} className={styles.actionRow}>
                  <div className={styles.actionTop}>
                    <label className={styles.actionCheck}>
                      <input
                        type="checkbox"
                        checked={item.status === "done"}
                        onChange={() => void onToggleAction(item.id, item.status)}
                        disabled={editingLocked}
                      />
                      <span className="muted">완료</span>
                    </label>
                    <div className={styles.actionButtons}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => void onSaveAction(item.id)}
                        disabled={editingLocked}
                      >
                        액션 저장
                      </button>
                      <button
                        type="button"
                        className="btn btn-danger"
                        onClick={() => void onDeleteAction(item.id)}
                        disabled={editingLocked}
                      >
                        삭제
                      </button>
                    </div>
                  </div>

                  <label className={styles.field}>
                    <span>할 일</span>
                    <input
                      value={draft.task}
                      onChange={(e) => patchDraft(item.id, "task", e.target.value)}
                      disabled={editingLocked}
                      className={item.status === "done" ? styles.doneText : undefined}
                    />
                  </label>

                  <div className={styles.actionFields}>
                    <label className={styles.field}>
                      <span>담당자</span>
                      <input
                        value={draft.assignee}
                        onChange={(e) =>
                          patchDraft(item.id, "assignee", e.target.value)
                        }
                        placeholder="없으면 비워 두세요"
                        disabled={editingLocked}
                      />
                    </label>
                    <label className={styles.field}>
                      <span>기한</span>
                      <input
                        type="date"
                        value={draft.due_date}
                        onChange={(e) =>
                          patchDraft(item.id, "due_date", e.target.value)
                        }
                        disabled={editingLocked}
                      />
                    </label>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
