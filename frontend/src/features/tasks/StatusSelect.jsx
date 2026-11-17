import { ChevronDownIcon, LockIcon } from "../../core/ui/icons";
import { cn } from "../../core/utils/cn";
import { STATUSES } from "./taskDisplay";

/**
 * StatusSelect — UI-DESIGN §5. 칸반은 드래그가 아니라 이 드롭다운으로 상태를 바꾼다(CLAUDE.md §3).
 * 권한이 없으면 🔒 + 읽기 전용으로 보여 준다. 버튼 숨김은 편의 기능이고, 권한 판단은 백엔드가 한다.
 *
 * @param {"TODO"|"IN_PROGRESS"|"DONE"} value
 * @param {(status: string) => void} onChange 값이 실제로 바뀔 때만 부른다
 * @param {boolean} readOnly 권한 없음 → 🔒 표시
 * @param {boolean} disabled 요청 중 등 잠시 막을 때
 */
export default function StatusSelect({
  value,
  onChange,
  readOnly = false,
  disabled = false,
  className,
}) {
  const current = STATUSES[value] ?? STATUSES.TODO;

  if (readOnly) {
    return (
      <span
        title="상태를 바꿀 권한이 없습니다"
        className={cn(
          "inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-neutral-500",
          className,
        )}
      >
        <span className={cn("size-2 rounded-full", current.dot)} />
        {current.label}
        <LockIcon size={12} className="text-neutral-400" />
        <span className="sr-only">(변경 권한 없음)</span>
      </span>
    );
  }

  return (
    <span className={cn("relative inline-flex items-center", className)}>
      <span
        className={cn(
          "pointer-events-none absolute left-2 size-2 rounded-full",
          current.dot,
        )}
      />
      <select
        aria-label="상태"
        value={value}
        disabled={disabled}
        onChange={(e) => {
          if (e.target.value !== value) onChange?.(e.target.value);
        }}
        // 카드 안에서 쓸 때 카드 클릭(상세 열기)으로 번지지 않게 한다.
        onClick={(e) => e.stopPropagation()}
        className="cursor-pointer appearance-none rounded-lg border border-neutral-200 bg-white py-1 pr-6 pl-5 text-xs text-neutral-700 hover:border-neutral-300 focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
      >
        {Object.entries(STATUSES).map(([key, { label }]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
      <ChevronDownIcon
        size={12}
        className="pointer-events-none absolute right-2 text-neutral-500"
      />
    </span>
  );
}
