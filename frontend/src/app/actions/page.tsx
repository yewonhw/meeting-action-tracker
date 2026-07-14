/**
 * /actions — 여러 회의 액션 보드 (서버사이드 필터·정렬)
 *
 * ------------------------------------------------------------------
 * 왜 이 페이지를 만들었나?
 * - 담당자/기한/상태 필터·정렬을 프론트 array.filter 이 아니라 서버 쿼리로 처리
 * - 회의 상세만 있으면 "한 회의 안" 액션만 보이고, 가로지르는 조회가 없음
 * - 그래서 /actions + GET /api/action-items?... 로 전체 액션을 조회·필터
 *
 * 왜 URL 쿼리 = 서버 쿼리인가?
 * - 적용 버튼을 누르면 router.push(/actions?assignee=...&status=...)
 * - useSearchParams 로 읽은 값이 곧 listActionItems() 인자
 * - 새로고침·링크 공유 시에도 같은 필터가 유지됨
 * - "화면 state 만 바꾸고 목록은 그대로 두고 JS 로 거르기" 패턴을 피함
 *
 * 데이터 흐름:
 *   폼 입력(draft*) → 적용 → URL 갱신 → useEffect → GET /api/action-items → setItems
 * ------------------------------------------------------------------
 */

"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { listActionItems, updateActionItem } from "@/lib/api";
import type {
  ActionItemListItem,
  ActionSortBy,
  ActionStatus,
  SortDir,
} from "@/lib/types";
import styles from "./actions.module.css";

function ActionsBoardInner() {
  const router = useRouter();
  // App Router: 현재 URL 의 ?query 를 읽음. 서버 컴포넌트가 아니라 클라이언트에서 씀
  const searchParams = useSearchParams();

  // ---- 실제 서버에 보낼 조건 (URL 이 단일 출처) ----
  const assignee = searchParams.get("assignee") ?? "";
  const status = (searchParams.get("status") ?? "") as "" | ActionStatus;
  const dueTo = searchParams.get("due_to") ?? "";
  // 기본 정렬: 기한 오름차순 (할 일 보드에서 가장 흔한 요구)
  const sortBy = (searchParams.get("sort_by") ?? "due_date") as ActionSortBy;
  const sortDir = (searchParams.get("sort_dir") ?? "asc") as SortDir;

  // null = 아직 첫 응답 전 / [] = 응답은 왔는데 0건
  const [items, setItems] = useState<ActionItemListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  /**
   * draft* = 폼에 보이는 값.
   * 왜 URL 과 폼을 나누나?
   * - 입력 중마다 서버를 치면 요청이 폭주하고, 타이핑 UX 도 나쁨
   * - "적용" 할 때만 URL(및 서버 조회)을 바꾸기 위해 draft 를 둠
   */
  const [draftAssignee, setDraftAssignee] = useState(assignee);
  const [draftStatus, setDraftStatus] = useState(status);
  const [draftDueTo, setDraftDueTo] = useState(dueTo);
  const [draftSortBy, setDraftSortBy] = useState(sortBy);
  const [draftSortDir, setDraftSortDir] = useState(sortDir);

  // 뒤로가기/초기화로 URL 만 바뀐 경우 draft 를 URL 에 맞춤
  useEffect(() => {
    setDraftAssignee(assignee);
    setDraftStatus(status);
    setDraftDueTo(dueTo);
    setDraftSortBy(sortBy);
    setDraftSortDir(sortDir);
  }, [assignee, status, dueTo, sortBy, sortDir]);

  // URL 조건이 바뀔 때마다 서버에 다시 요청 (여기서 items 를 로컬 filter 하지 않음)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listActionItems({
          assignee: assignee || undefined,
          status: status || undefined,
          due_to: dueTo || undefined,
          sort_by: sortBy,
          sort_dir: sortDir,
        });
        if (!cancelled) {
          setItems(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "목록을 불러오지 못했습니다.");
          setItems([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [assignee, status, dueTo, sortBy, sortDir]);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (draftAssignee.trim()) next.set("assignee", draftAssignee.trim());
    if (draftStatus) next.set("status", draftStatus);
    if (draftDueTo) next.set("due_to", draftDueTo);
    next.set("sort_by", draftSortBy);
    next.set("sort_dir", draftSortDir);
    router.push(`/actions?${next.toString()}`);
  }

  function clearFilters() {
    // 쿼리 없는 /actions → 전체 목록 + 기본 정렬
    router.push("/actions");
  }

  async function onToggle(id: number, current: string) {
    const next = current === "done" ? "todo" : "done";
    setBusyId(id);
    try {
      await updateActionItem(id, { status: next });
      /**
       * 왜 setItems 로 해당 행만 안 고치나?
       * - 지금 status=todo 필터인데 done 으로 바꾸면, 서버 기준으로는 목록에서 빠져야 함
       * - 로컬만 토글하면 필터와 불일치 → 다시 listActionItems(현재 URL 조건) 호출
       */
      const data = await listActionItems({
        assignee: assignee || undefined,
        status: status || undefined,
        due_to: dueTo || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      });
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "상태 변경 실패");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main>
      <h1 className={styles.title}>액션 보드</h1>
      <p className={`muted ${styles.lead}`}>
        담당자·기한·상태 필터와 정렬은 서버 쿼리(
        <code>GET /api/action-items</code>)로 처리합니다. 프론트에서 목록을 거르지
        않습니다.
      </p>

      <form className={styles.filters} onSubmit={applyFilters}>
        <label className={styles.field}>
          <span>담당자</span>
          <input
            value={draftAssignee}
            onChange={(e) => setDraftAssignee(e.target.value)}
            placeholder="예: 민수"
          />
        </label>
        <label className={styles.field}>
          <span>상태</span>
          <select
            value={draftStatus}
            onChange={(e) =>
              setDraftStatus(e.target.value as "" | ActionStatus)
            }
          >
            <option value="">전체</option>
            <option value="todo">할 일</option>
            <option value="done">완료</option>
          </select>
        </label>
        <label className={styles.field}>
          <span>마감일까지</span>
          {/* due_to: 이 날짜 이하(지난 마감 포함). "그날만"이 아니라 "~까지" */}
          <input
            type="date"
            value={draftDueTo}
            onChange={(e) => setDraftDueTo(e.target.value)}
          />
        </label>
        <label className={styles.field}>
          <span>정렬</span>
          <select
            value={draftSortBy}
            onChange={(e) => setDraftSortBy(e.target.value as ActionSortBy)}
          >
            <option value="due_date">마감일</option>
            <option value="assignee">담당자</option>
            <option value="status">상태</option>
            <option value="created_at">생성일</option>
          </select>
        </label>
        <label className={styles.field}>
          <span>방향</span>
          <select
            value={draftSortDir}
            onChange={(e) => setDraftSortDir(e.target.value as SortDir)}
          >
            <option value="asc">오름차순</option>
            <option value="desc">내림차순</option>
          </select>
        </label>
        <div className={styles.filterActions}>
          <button type="submit" className="btn btn-primary">
            적용
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={clearFilters}
          >
            초기화
          </button>
        </div>
      </form>

      {error ? <p className={styles.error}>{error}</p> : null}
      {items === null ? <p className="muted">불러오는 중…</p> : null}
      {items && items.length === 0 && !error ? (
        <p className="muted">조건에 맞는 액션이 없습니다.</p>
      ) : null}

      {items && items.length > 0 ? (
        <ul className={styles.list}>
          {items.map((item) => (
            <li key={item.id} className={styles.row}>
              <label className={styles.check}>
                <input
                  type="checkbox"
                  checked={item.status === "done"}
                  disabled={busyId === item.id}
                  onChange={() => void onToggle(item.id, item.status)}
                />
                <span className="muted">완료</span>
              </label>
              <div className={styles.body}>
                <div
                  className={
                    item.status === "done" ? styles.taskDone : styles.task
                  }
                >
                  {item.task}
                </div>
                <div className={`muted ${styles.meta}`}>
                  {/* 어느 회의인지 바로 상세로 */}
                  <Link href={`/meetings/${item.meeting_id}`}>
                    {item.meeting_title}
                  </Link>
                  {" · "}
                  {item.assignee ?? "담당자 없음"}
                  {" · "}
                  {item.due_date ?? "기한 없음"}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}

/**
 * useSearchParams 는 Suspense boundary 가 필요함 (Next.js App Router).
 * page 전체를 client 로 두고 Inner 만 suspense 로 감싸 빌드 경고를 피한다.
 */
export default function ActionsPage() {
  return (
    <Suspense fallback={<main><p className="muted">불러오는 중…</p></main>}>
      <ActionsBoardInner />
    </Suspense>
  );
}
