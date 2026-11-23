import { useId, useState } from "react";
import { cn } from "../../core/utils/cn";
import TaskActivityList from "./TaskActivityList";
import TaskComments from "./TaskComments";

// 업무 상세 왼쪽 아래 탭 묶음 `[댓글 | 변경 이력 n]` — UI-DESIGN S6, CMT-01·02 · LOG-03-a (P1)
// 탭 틀과 변경 이력 탭은 T-F4-06(최진영), 댓글 탭 내용은 T-F4-04(서승범)가 아래 "댓글 자리"에 끼운다.
// 순서는 시안대로 댓글이 앞이다.

// 처음 열리는 탭 — 시안 순서대로 댓글
const DEFAULT_TAB = "comments";

/**
 * @param {number} taskId
 * @param {number} historyVersion 상세에서 속성을 저장할 때마다 바뀌는 값 → 이력을 다시 불러온다
 */
export default function TaskDetailTabs({ taskId, historyVersion }) {
  const baseId = useId();
  const [tab, setTab] = useState(DEFAULT_TAB);
  const [historyTotal, setHistoryTotal] = useState(null);
  const [commentTotal, setCommentTotal] = useState(null);

  const tabs = [
    { key: "comments", label: "댓글", count: commentTotal },
    { key: "history", label: "변경 이력", count: historyTotal },
  ];

  return (
    <section className="flex flex-col gap-3">
      <div
        role="tablist"
        aria-label="댓글과 변경 이력"
        className="flex gap-1 border-b border-neutral-200"
      >
        {tabs.map((t) => {
          const selected = tab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              role="tab"
              id={`${baseId}-${t.key}-tab`}
              aria-selected={selected}
              aria-controls={`${baseId}-${t.key}-panel`}
              onClick={() => setTab(t.key)}
              className={cn(
                "-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-semibold",
                selected
                  ? "border-primary text-primary"
                  : "border-transparent text-neutral-500 hover:text-neutral-700",
              )}
            >
              {t.label}
              {t.count != null && (
                <span className="rounded-md bg-neutral-100 px-1.5 text-xs text-neutral-600">
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`${baseId}-comments-panel`}
        aria-labelledby={`${baseId}-comments-tab`}
        hidden={tab !== "comments"}
      >
        {/* 댓글 — T-F4-04. 탭을 바꿔도 입력 중인 글이 남도록 hidden으로만 숨긴다 */}
        <TaskComments taskId={taskId} onCountChange={setCommentTotal} />
      </div>

      {/* 변경 이력 — 탭을 바꿔도 목록을 유지하도록 hidden으로만 숨긴다 */}
      <div
        role="tabpanel"
        id={`${baseId}-history-panel`}
        aria-labelledby={`${baseId}-history-tab`}
        hidden={tab !== "history"}
      >
        <TaskActivityList
          taskId={taskId}
          version={historyVersion}
          onTotal={setHistoryTotal}
        />
      </div>
    </section>
  );
}
