// 업무 권한 — REQUIREMENTS TASK-06 권한 매트릭스, UI-DESIGN S6 "권한별 화면 상태".
// 화면에서 🔒·버튼 숨김을 정하는 편의 기능일 뿐이다. 실제 권한 판단은 백엔드가 한다.
//
// | 보는 사람                     | 제목·설명 | 상태 | 우선순위·담당자·마감일 | 삭제 |
// | OWNER                         | 수정      | 수정 | 수정                   | 보임 |
// | MEMBER + 작성자               | 수정      | 수정 | 수정                   | 보임 |
// | MEMBER + 담당자(작성자 아님)  | 읽기      | 수정 | 🔒 읽기                | 숨김 |
// | 그 외 MEMBER                  | 읽기      | 🔒   | 🔒 읽기                | 숨김 |

/**
 * @param {object} task API-SPEC §4 Task
 * @param {"OWNER"|"MEMBER"} myRole Project.my_role
 * @param {number} myId 로그인한 사용자 id
 * @returns {{ canEdit: boolean, canChangeStatus: boolean, canDelete: boolean }}
 *   canEdit = 상태 외 모든 항목 수정
 */
export function getTaskPermissions(task, myRole, myId) {
  const ownerOrAuthor = myRole === "OWNER" || task.created_by?.id === myId;
  const assignee = task.assignee?.id === myId;
  return {
    canEdit: ownerOrAuthor,
    canChangeStatus: ownerOrAuthor || assignee,
    canDelete: ownerOrAuthor,
  };
}

/** 카드(S4)용 — 상태를 바꿀 수 있는가 */
export function canChangeStatus(task, myRole, myId) {
  return getTaskPermissions(task, myRole, myId).canChangeStatus;
}
