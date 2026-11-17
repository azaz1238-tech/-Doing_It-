import { cn } from "../../core/utils/cn";
import { PRIORITIES } from "./taskDisplay";

/**
 * PriorityBadge — UI-DESIGN §5·§6.1. 카드·상세에서 쓴다.
 * @param {"URGENT"|"HIGH"|"MEDIUM"|"LOW"} priority
 */
export default function PriorityBadge({ priority, className }) {
  const item = PRIORITIES[priority] ?? PRIORITIES.MEDIUM;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-xs font-semibold",
        item.className,
        className,
      )}
    >
      {item.label}
    </span>
  );
}
