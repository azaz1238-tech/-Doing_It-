import Avatar from "../../core/ui/Avatar";
import { cn } from "../../core/utils/cn";
import DueLabel from "./DueLabel";
import PriorityBadge from "./PriorityBadge";
import StatusSelect from "./StatusSelect";

/**
 * TaskCard — UI-DESIGN §5·S4. 우선순위 · DueLabel · 제목 · 담당자 · StatusSelect.
 * 완료(DONE) 카드는 제목에 취소선, 마감 표시는 숨긴다(§6.2).
 *
 * @param {object} task API-SPEC §4 Task
 * @param {boolean} canChangeStatus false면 StatusSelect가 🔒 읽기 전용
 * @param {boolean} updating 상태 변경 요청 중
 * @param {(status: string) => void} onStatusChange
 * @param {() => void} onOpen 카드 본문 클릭 → 업무 상세(S6)
 */
export default function TaskCard({
  task,
  canChangeStatus,
  updating = false,
  onStatusChange,
  onOpen,
}) {
  const done = task.status === "DONE";

  return (
    <article className="rounded-lg border border-neutral-200 bg-white p-3 shadow-xs transition hover:border-neutral-300 hover:shadow-sm">
      <div className="flex items-center gap-2">
        <PriorityBadge priority={task.priority} />
        <DueLabel dueDate={task.due_date} status={task.status} />
      </div>

      {/* 카드 본문 클릭 → 상세. 키보드로도 열 수 있게 버튼으로 둔다. */}
      <button
        type="button"
        onClick={onOpen}
        className={cn(
          "mt-2 block w-full rounded text-left text-[15px] font-bold break-words text-neutral-900 hover:text-primary focus-visible:outline-2 focus-visible:outline-primary",
          done && "text-neutral-400 line-through hover:text-neutral-500",
        )}
      >
        {task.title}
      </button>

      <div className="mt-3 flex items-center justify-between gap-2">
        <Avatar user={task.assignee} size="sm" />
        <StatusSelect
          value={task.status}
          readOnly={!canChangeStatus}
          disabled={updating}
          onChange={onStatusChange}
        />
      </div>
    </article>
  );
}
