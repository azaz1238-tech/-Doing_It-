import client from "../../core/api/client";

// 업무 API (API-SPEC §5.4). 화면에서 axios를 직접 부르지 않는다(ARCHITECTURE §5).

/**
 * 칸반 컬럼 하나 — 컬럼(status)마다 1번씩 부른다. 정렬은 서버 정렬 그대로.
 * 검색·필터(P1, TASK-07): q · assignee_id(`none` = 담당자 없음) · priority · due_from · due_to
 */
export async function listTasks(
  projectId,
  { status, page = 1, size = 20, ...filters },
) {
  const { data } = await client.get(`/projects/${projectId}/tasks`, {
    params: { ...filters, status, page, size },
  });
  return data; // { items: Task[], total, page, size }
}

/**
 * 내 업무 대시보드 (DASH-04, API-SPEC §6 `GET /users/me/tasks`).
 * 모든 프로젝트에서 나에게 할당된 미완료 업무. 정렬은 서버가 한다: 지연 → 임박 → 나머지, 마감일 순(없음은 뒤) → id.
 * 각 항목에 project { id, name }, alert("OVERDUE" | "DUE_SOON" | null)가 붙는다. 화면은 최대 100건을 한 번에 받는다.
 */
export async function listMyTasks({ page = 1, size = 100 } = {}) {
  const { data } = await client.get("/users/me/tasks", {
    params: { page, size },
  });
  return data; // { items: MyTask[], total, page, size }
}

/**
 * 업무 변경 이력 (LOG-03-a, API-SPEC §6). 최신순(created_at DESC, id DESC).
 * 한 업무의 이력은 많지 않아 상세 탭은 최대 100건을 한 번에 받는다. 비멤버 403, 업무 없음 404
 */
export async function listTaskActivities(taskId, { size = 100 } = {}) {
  const { data } = await client.get(`/tasks/${taskId}/activities`, {
    params: { page: 1, size },
  });
  return data; // { items: Activity[], total, page, size }
}

/** 업무 등록 — status는 보내지 않는다(항상 TODO). 비어 있는 선택 필드는 빼고 보낸다 */
export async function createTask(projectId, body) {
  const { data } = await client.post(`/projects/${projectId}/tasks`, body);
  return data; // Task
}

/** 업무 수정·상태 변경 — 바꿀 필드만 보낸다 */
export async function updateTask(taskId, patch) {
  const { data } = await client.patch(`/tasks/${taskId}`, patch);
  return data; // Task
}

/** 업무 상세 — 업무가 속한 프로젝트 멤버만(아니면 403 NOT_PROJECT_MEMBER) */
export async function getTask(taskId) {
  const { data } = await client.get(`/tasks/${taskId}`);
  return data; // Task
}

/** 업무 삭제 — OWNER·작성자만(아니면 403 FORBIDDEN). 이력은 남는다 */
export async function deleteTask(taskId) {
  await client.delete(`/tasks/${taskId}`); // 204
}

// --- 댓글 (CMT-01·02, API-SPEC §6) ---
// Comment: { id, task_id, user: { id, login_id, name }, content, created_at, updated_at }
// 화면은 updated_at이 created_at과 다르면 "수정됨"을 표시한다(UI-DESIGN §9 #6).

/** 댓글 목록 — 오래된 순. 멤버 누구나 */
export async function listComments(taskId, { page = 1, size = 100 } = {}) {
  const { data } = await client.get(`/tasks/${taskId}/comments`, {
    params: { page, size },
  });
  return data; // { items: Comment[], total, page, size }
}

/** 댓글 작성 — 앞뒤 공백 제거 후 1~300자(아니면 422) */
export async function createComment(taskId, content) {
  const { data } = await client.post(`/tasks/${taskId}/comments`, { content });
  return data; // Comment
}

/** 댓글 수정 — 작성자만(OWNER도 남의 댓글은 403 FORBIDDEN) */
export async function updateComment(commentId, content) {
  const { data } = await client.patch(`/comments/${commentId}`, { content });
  return data; // Comment
}

/** 댓글 삭제 — 작성자만 */
export async function deleteComment(commentId) {
  await client.delete(`/comments/${commentId}`); // 204
}
