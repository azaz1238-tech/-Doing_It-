import client from "../../core/api/client";

// 프로젝트 API (API-SPEC §5.2). 화면에서 axios를 직접 부르지 않는다(ARCHITECTURE §5).

// P0은 프로젝트 수가 적어 최대 100건을 한 번에 받는다(페이지 이동 UI 없음).
export async function listProjects({ page = 1, size = 100 } = {}) {
  const { data } = await client.get("/projects", { params: { page, size } });
  return data; // { items: Project[], total, page, size } — created_at 최신순
}

export async function createProject({ name, description, startDate, endDate }) {
  const { data } = await client.post("/projects", {
    name,
    description: description || null,
    start_date: startDate || null, // 빈 문자열은 422라서 null로 보낸다
    end_date: endDate || null,
  });
  return data; // Project (my_role: "OWNER")
}

// 프로젝트 상세 (PRJ-07). 칸반(S4)이 이름·기간·내 역할(my_role)을 읽는다.
// 비멤버 403 NOT_PROJECT_MEMBER, 없으면 404 PROJECT_NOT_FOUND
export async function getProject(projectId) {
  const { data } = await client.get(`/projects/${projectId}`);
  return data; // Project
}

// 멤버 목록 (PRJ-07, API-SPEC §5.3). OWNER 먼저 → joined_at → id 순.
// S4 헤더 아바타 묶음·담당자 선택지(S5)·S7 멤버 목록이 같이 쓴다. 화면은 size=100.
// 비멤버 403 NOT_PROJECT_MEMBER, 없으면 404 PROJECT_NOT_FOUND
export async function listMembers(projectId, { page = 1, size = 100 } = {}) {
  const { data } = await client.get(`/projects/${projectId}/members`, {
    params: { page, size },
  });
  return data; // { items: Member[], total, page, size }
}

// 프로젝트 수정 (PRJ-03, OWNER). 바꿀 필드만 snake_case로 보낸다.
// description·날짜는 null로 비울 수 있고 name은 비울 수 없다. MEMBER 403 FORBIDDEN, 422 errors[]
export async function updateProject(projectId, patch) {
  const { data } = await client.patch(`/projects/${projectId}`, patch);
  return data; // Project
}

// 프로젝트 삭제 (PRJ-03, OWNER). 업무·댓글·이력이 CASCADE로 함께 지워진다.
// 이름 확인 절차는 화면(S7 확인 창)에서만 한다. 응답 204
export async function deleteProject(projectId) {
  await client.delete(`/projects/${projectId}`);
}
