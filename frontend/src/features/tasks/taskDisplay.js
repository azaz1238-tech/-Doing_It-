import { ClockIcon, TriangleAlertIcon } from "../../core/ui/icons";
import { daysBetween, formatMonthDay } from "../../core/utils/date";
import { cn } from "../../core/utils/cn";

// 업무 표시 규칙 — UI-DESIGN §6. 배지 컴포넌트와 등록·상세 모달의 선택 목록이 함께 쓴다.
// Tailwind가 클래스를 찾을 수 있도록 전체 이름을 그대로 적는다(문자열 조합 금지).

// §6.1 우선순위 (긴급 빨강, 높음 주황, 보통 파랑, 낮음 회색)
export const PRIORITIES = {
  URGENT: { label: "긴급", className: "bg-danger-soft text-danger" },
  HIGH: { label: "높음", className: "bg-warning-soft text-warning" },
  MEDIUM: { label: "보통", className: "bg-primary-soft text-info" },
  LOW: { label: "낮음", className: "bg-neutral-100 text-neutral-500" },
};

// §6.2 상태. 순서는 칸반 컬럼 순서와 같고, 어느 방향으로든 바꿀 수 있다(TASK-02).
export const STATUSES = {
  TODO: { label: "할 일", dot: "bg-neutral-400" },
  IN_PROGRESS: { label: "진행 중", dot: "bg-primary" },
  DONE: { label: "완료", dot: "bg-success" },
};

const BADGE =
  "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-semibold";
const SOON = cn(BADGE, "bg-warning-soft text-warning");

/**
 * §6.3 마감 표시. 임박 범위(오늘 ~ +3일)는 DASH-03과 같다.
 * @param {string|null} dueDate "YYYY-MM-DD"
 * @param {string} today 한국 날짜 "YYYY-MM-DD"
 * @returns {{ text: string, className: string, Icon?: Function }}
 */
export function getDueInfo(dueDate, today) {
  if (!dueDate)
    return { text: "마감 없음", className: "text-xs text-neutral-400" };

  const diff = daysBetween(today, dueDate);

  if (diff < 0)
    return {
      text: `${-diff}일 지남`,
      className: cn(BADGE, "bg-danger-soft text-danger"),
      Icon: TriangleAlertIcon,
    };
  if (diff === 0)
    return { text: "오늘 마감", className: SOON, Icon: ClockIcon };
  if (diff === 1) return { text: "내일 마감", className: SOON };
  if (diff <= 3) return { text: `D-${diff}`, className: SOON };
  return {
    text: formatMonthDay(dueDate),
    className: "text-xs text-neutral-500",
  };
}
