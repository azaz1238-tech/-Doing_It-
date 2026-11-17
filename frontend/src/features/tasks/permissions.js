// 업무 권한 — REQUIREMENTS TASK-06 권한 매트릭스.
// 화면에서 🔒를 보여 주는 편의 기능일 뿐이다. 실제 권한 판단은 백엔드(require_project_role)가 한다.

/**
 * 상태를 바꿀 수 있는가: OWNER는 모든 업무, MEMBER는 본인이 작성했거나 본인이 담당자인 업무.
 * @param {object} task API-SPEC §4 Task
 * @param {"OWNER"|"MEMBER"} myRole Project.my_role
 * @param {number} myId 로그인한 사용자 id
 */
export function canChangeStatus(task, myRole, myId) {
  if (myRole === "OWNER") return true;
  return task.created_by?.id === myId || task.assignee?.id === myId;
}
