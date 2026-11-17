import { todayKst } from "../../core/utils/date";
import { cn } from "../../core/utils/cn";
import { getDueInfo } from "./taskDisplay";

/**
 * DueLabel — UI-DESIGN §5·§6.3. "오늘"은 한국 날짜(API-SPEC §1.6).
 * 완료된 업무에는 표시하지 않는다.
 *
 * @param {string|null} dueDate "YYYY-MM-DD" 또는 null
 * @param {"TODO"|"IN_PROGRESS"|"DONE"} status
 * @param {string} today 미리보기·테스트용으로 오늘 날짜를 고정할 때만 넘긴다
 */
export default function DueLabel({ dueDate, status, today, className }) {
  if (status === "DONE") return null;

  const info = getDueInfo(dueDate, today ?? todayKst());
  const Icon = info.Icon;

  return (
    <span className={cn(info.className, className)}>
      {Icon && <Icon size={12} />}
      {info.text}
    </span>
  );
}
