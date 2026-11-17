// 칸반 목 데이터 — T-F2-10 퍼블리싱용. API-SPEC §4 Task·§1.3 목록 응답 모양을 그대로 따른다.
// TODO(T-F2-11): 업무 API가 나오면 api.js로 바꾸고 이 파일은 지운다.

export const MOCK_ME = { id: 2, login_id: "minho", name: "김민호" };

export const MOCK_PROJECT = {
  id: 10,
  name: "백엔드 MVP",
  description: "11월 팀 프로젝트",
  start_date: "2026-11-10",
  end_date: "2026-11-19",
  my_role: "MEMBER", // 🔒 표시를 보기 위해 MEMBER로 둔다
  created_at: "2026-11-10T00:00:00Z",
  updated_at: "2026-11-10T00:00:00Z",
};

const USERS = {
  jisoo: { id: 1, login_id: "jisoo01", name: "이지수" },
  minho: MOCK_ME,
  seoyeon: { id: 3, login_id: "seoyeon", name: "박서연" },
  hyunwoo: { id: 4, login_id: "hyunwoo", name: "최현우" },
};

let nextId = 100;
function task(title, status, priority, assignee, dueDate, createdBy) {
  const id = nextId++;
  return {
    id,
    project_id: MOCK_PROJECT.id,
    title,
    description: "",
    status,
    priority,
    assignee,
    due_date: dueDate,
    created_by: createdBy,
    completed_at: status === "DONE" ? "2026-11-15T09:00:00Z" : null,
    created_at: "2026-11-11T05:30:00Z",
    updated_at: "2026-11-12T01:00:00Z",
  };
}

const { jisoo, minho, seoyeon, hyunwoo } = USERS;

// 오늘(11/17) 기준으로 지연·오늘·내일·D-3·그 이후·마감 없음이 모두 보이게 섞었다.
const tasks = [
  task("업무 상태 변경 API", "TODO", "URGENT", minho, "2026-11-15", jisoo),
  task(
    "로그인 화면 오류 문구 정리",
    "TODO",
    "HIGH",
    seoyeon,
    "2026-11-17",
    seoyeon,
  ),
  task("프로젝트 목록 API", "TODO", "MEDIUM", null, "2026-11-18", jisoo),
  task("시드 데이터 스크립트 작성", "TODO", "LOW", hyunwoo, null, hyunwoo),
  task("칸반 보드 API 연결", "IN_PROGRESS", "HIGH", minho, "2026-11-20", minho),
  task(
    "업무 등록 모달 검증 문구",
    "IN_PROGRESS",
    "MEDIUM",
    jisoo,
    "2026-11-25",
    jisoo,
  ),
  task(
    "멤버 추가 API 권한 테스트",
    "IN_PROGRESS",
    "URGENT",
    hyunwoo,
    "2026-11-16",
    jisoo,
  ),
  task("회원가입 API", "DONE", "HIGH", jisoo, "2026-11-14", jisoo),
  // "n개 더 보기"를 보기 위해 완료 컬럼은 한 페이지(20개)보다 많게 만든다.
  ...Array.from({ length: 21 }, (_, i) =>
    task(
      `완료된 업무 ${i + 1}`,
      "DONE",
      ["MEDIUM", "LOW"][i % 2],
      [minho, seoyeon, null][i % 3],
      i % 4 === 0 ? null : "2026-11-13",
      jisoo,
    ),
  ),
];

// 서버 정렬과 같게: 우선순위 높은 순 → 마감일 빠른 순(없음은 뒤) → id (API-SPEC §5.4)
const PRIORITY_ORDER = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
function compare(a, b) {
  return (
    PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] ||
    (a.due_date ?? "9999-12-31").localeCompare(b.due_date ?? "9999-12-31") ||
    a.id - b.id
  );
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** GET /projects/{id}/tasks?status=&page=&size= 흉내 */
export async function fetchMockTasks({ status, page = 1, size = 20 }) {
  await delay(300);
  const filtered = tasks.filter((t) => t.status === status).sort(compare);
  const start = (page - 1) * size;
  return {
    items: filtered.slice(start, start + size),
    total: filtered.length,
    page,
    size,
  };
}

/** PATCH /tasks/{id} {status} 흉내 */
export async function updateMockTaskStatus(taskId, status) {
  await delay(200);
  const target = tasks.find((t) => t.id === taskId);
  target.status = status;
  target.completed_at = status === "DONE" ? new Date().toISOString() : null;
  return { ...target };
}
