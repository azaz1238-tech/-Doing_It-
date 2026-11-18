import client from "../../core/api/client";

// 업무 API (API-SPEC §5.4). 화면에서 axios를 직접 부르지 않는다(ARCHITECTURE §5).

/** 칸반 컬럼 하나 — 컬럼(status)마다 1번씩 부른다. 정렬은 서버 정렬 그대로 */
export async function listTasks(projectId, { status, page = 1, size = 20 }) {
  const { data } = await client.get(`/projects/${projectId}/tasks`, {
    params: { status, page, size },
  });
  return data; // { items: Task[], total, page, size }
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
