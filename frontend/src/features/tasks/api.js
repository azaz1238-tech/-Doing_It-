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
