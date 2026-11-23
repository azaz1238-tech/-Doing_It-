import { formatMonthDay } from "../../core/utils/date";
import { PRIORITIES, STATUSES } from "./taskDisplay";

// 변경 이력(Activity) 한 행을 화면 문구로 — LOG-03, API-SPEC §6 "변경 이력", DATABASE-DESIGN §4.5 행 모양.
// 프로젝트 최근 활동(통계 탭, T-F4-07)과 업무 상세 이력 탭(LOG-03-a)이 함께 쓴다.

const EMPTY = "없음";

const FIELD_LABELS = {
  status: "상태",
  assignee_id: "담당자",
  due_date: "마감일",
  priority: "우선순위",
};

// field별 값 → 화면 글자. 모르는 값은 서버 값을 그대로 보여 준다.
function valueText(activity, side) {
  const { field } = activity;
  if (field === "assignee_id") {
    // 담당자는 서버가 id 대신 UserBrief를 함께 준다(null = 담당자 없음)
    return activity[`${side}_assignee`]?.name ?? EMPTY;
  }
  const raw = activity[`${side}_value`];
  if (raw == null) return EMPTY;
  if (field === "status") return STATUSES[raw]?.label ?? raw;
  if (field === "priority") return PRIORITIES[raw]?.label ?? raw;
  if (field === "due_date") return formatMonthDay(raw); // 11/20
  return raw;
}

/**
 * 무엇이 바뀌었는지. 예: "업무 생성", "마감일 11/20 → 11/25"
 * @param {object} activity API Activity
 */
export function describeActivity(activity) {
  if (activity.action === "CREATED") return "업무 생성";
  if (activity.action === "DELETED") return "업무 삭제";
  const label = FIELD_LABELS[activity.field] ?? activity.field;
  return `${label} ${valueText(activity, "old")} → ${valueText(activity, "new")}`;
}

/**
 * 어떤 업무의 이력인지. 삭제된 업무는 DELETED 행만 삭제 전 제목(old_value)을 알고,
 * 나머지 행은 task_title이 null이라 "삭제된 업무"로 보여 준다(API-SPEC §6).
 * @param {object} activity API Activity
 */
export function activityTaskTitle(activity) {
  if (activity.task_title) return activity.task_title;
  if (activity.action === "DELETED" && activity.old_value)
    return activity.old_value;
  return "삭제된 업무";
}
