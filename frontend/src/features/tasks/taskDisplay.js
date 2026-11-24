import { ClockIcon, TriangleAlertIcon } from "../../core/ui/icons";
import { daysBetween, formatMonthDay } from "../../core/utils/date";
import { cn } from "../../core/utils/cn";

// 업무 표시 규칙 — UI-DESIGN §6. 배지 컴포넌트와 등록·상세 모달의 선택 목록이 함께 쓴다.
// Tailwind가 클래스를 찾을 수 있도록 전체 이름을 그대로 적는다(문자열 조합 금지).

// §6.1 우선순위 (긴급 빨강, 높음 주황, 보통 파랑, 낮음 회색)
// className = 배지(배경+글자), text = 글자색만(등록 모달 세그먼트 선택 표시)
export const PRIORITIES = {
  URGENT: {
    label: "긴급",
    className: "bg-danger-soft text-danger",
    text: "text-danger",
  },
  HIGH: {
    label: "높음",
    className: "bg-warning-soft text-warning",
    text: "text-warning",
  },
  MEDIUM: {
    label: "보통",
    className: "bg-primary-soft text-info",
    text: "text-info",
  },
  LOW: {
    label: "낮음",
    className: "bg-neutral-100 text-neutral-500",
    text: "text-neutral-700",
  },
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
 * tone은 색 구분만 필요한 곳(간트 막대, TASK-12)이 같은 기준을 쓰도록 함께 돌려준다.
 * @returns {{ text: string, className: string, Icon?: Function, tone: "none"|"overdue"|"soon"|"normal" }}
 */
export function getDueInfo(dueDate, today) {
  if (!dueDate)
    return {
      text: "마감 없음",
      className: "text-xs text-neutral-400",
      tone: "none",
    };

  const diff = daysBetween(today, dueDate);

  if (diff < 0)
    return {
      text: `${-diff}일 지남`,
      className: cn(BADGE, "bg-danger-soft text-danger"),
      Icon: TriangleAlertIcon,
      tone: "overdue",
    };
  if (diff === 0)
    return {
      text: "오늘 마감",
      className: SOON,
      Icon: ClockIcon,
      tone: "soon",
    };
  if (diff === 1) return { text: "내일 마감", className: SOON, tone: "soon" };
  if (diff <= 3) return { text: `D-${diff}`, className: SOON, tone: "soon" };
  return {
    text: formatMonthDay(dueDate),
    className: "text-xs text-neutral-500",
    tone: "normal",
  };
}

// 글자 수 — 서버(Python `len`)와 같게 코드 포인트로 센다. 구현은 공통 유틸 하나만 둔다(#49).
export { countChars as charCount } from "../../core/utils/text";
