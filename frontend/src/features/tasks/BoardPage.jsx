import { useCallback, useEffect, useState } from "react";
import { Outlet, useNavigate } from "react-router";
import { useAuth } from "../../core/auth/useAuth";
import Button from "../../core/ui/Button";
import EmptyState from "../../core/ui/EmptyState";
import { ChevronDownIcon, PlusIcon } from "../../core/ui/icons";
import { SkeletonList } from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { formatPeriod } from "../../core/utils/date";
import {
  MOCK_ME,
  MOCK_PROJECT,
  fetchMockMembers,
  fetchMockTasks,
  updateMockTaskStatus,
} from "./mockData";
import { canChangeStatus } from "./permissions";
import TaskCard from "./TaskCard";
import TaskFormModal from "./TaskFormModal";
import { STATUSES } from "./taskDisplay";

// S4 칸반 보드 — UI-DESIGN §4 S4, TASK-02·TASK-05.
// TODO(T-F2-11): 목 데이터(mockData.js)를 features/tasks/api.js 호출로 바꾼다.
//   fetchMockTasks → GET /projects/{id}/tasks, updateMockTaskStatus → PATCH /tasks/{id},
//   MOCK_PROJECT → GET /projects/{id}, MOCK_ME → useAuth().user,
//   fetchMockMembers → GET /projects/{id}/members (양준석 T-F3-02)

const PAGE_SIZE = 20;
const COLUMN_ORDER = ["TODO", "IN_PROGRESS", "DONE"];

// 빈 컬럼 문구 — Figma "칸반 컬럼이 비었을 때"
const EMPTY_TEXT = {
  TODO: "할 일이 없습니다",
  IN_PROGRESS: "진행 중인 업무가 없습니다",
  DONE: "완료한 업무가 없습니다",
};

// 토스트 조사: 할 일·완료 → "로", 진행 중 → "으로"
const TO_PARTICLE = { TODO: "로", IN_PROGRESS: "으로", DONE: "로" };

const emptyColumn = () => ({ items: [], total: 0, page: 0, loading: true });

export default function BoardPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();
  const me = user ?? MOCK_ME;
  const project = MOCK_PROJECT;

  const [columns, setColumns] = useState(() =>
    Object.fromEntries(COLUMN_ORDER.map((s) => [s, emptyColumn()])),
  );
  const [updatingId, setUpdatingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  // 담당자 선택지(S5·S6)에 쓰는 멤버 목록. 보드에서 한 번 받아 모달에 넘긴다(UI-DESIGN S5).
  const [members, setMembers] = useState([]);

  const loadMembers = () =>
    fetchMockMembers().then((data) => setMembers(data.items));

  const patchColumn = (status, patch) =>
    setColumns((prev) => ({
      ...prev,
      [status]: { ...prev[status], ...patch },
    }));

  // 컬럼 하나를 첫 페이지부터 다시 불러온다.
  const loadColumn = useCallback(async (status) => {
    patchColumn(status, { loading: true });
    const data = await fetchMockTasks({ status, page: 1, size: PAGE_SIZE });
    patchColumn(status, {
      items: data.items,
      total: data.total,
      page: 1,
      loading: false,
    });
  }, []);

  useEffect(() => {
    COLUMN_ORDER.forEach(loadColumn);
    fetchMockMembers().then((data) => setMembers(data.items));
  }, [loadColumn]);

  // "n개 더 보기": 다음 page를 불러와 이어 붙인다.
  const loadMore = async (status) => {
    const col = columns[status];
    patchColumn(status, { loading: true });
    const data = await fetchMockTasks({
      status,
      page: col.page + 1,
      size: PAGE_SIZE,
    });
    setColumns((prev) => ({
      ...prev,
      [status]: {
        items: [...prev[status].items, ...data.items],
        total: data.total,
        page: data.page,
        loading: false,
      },
    }));
  };

  // 상태 변경 성공 → 바뀐 두 컬럼만 다시 조회 → 성공 토스트 (UI-DESIGN S4)
  const changeStatus = async (task, nextStatus) => {
    // 요청 전 상태를 따로 잡아 둔다(응답 뒤 task 값에 기대지 않는다).
    const prevStatus = task.status;
    setUpdatingId(task.id);
    try {
      await updateMockTaskStatus(task.id, nextStatus);
      await Promise.all([loadColumn(prevStatus), loadColumn(nextStatus)]);
      toast.success(
        `상태를 '${STATUSES[nextStatus].label}'${TO_PARTICLE[nextStatus]} 변경했습니다`,
      );
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* TODO: ProjectHeader(UI-DESIGN §3.2) 담당이 정해지면 교체한다. 지금은 이름·기간만 */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs text-neutral-500">프로젝트 ›</p>
          <h1 className="text-2xl font-bold">{project.name}</h1>
          <p className="mt-1 text-xs text-neutral-500">
            {/* 시작일·종료일은 선택 항목이라 없을 수 있다. S3 카드와 같게 "기간 없음" */}
            {formatPeriod(project.start_date, project.end_date) || "기간 없음"}
          </p>
        </div>
        {/* + 업무 추가는 헤더 오른쪽 버튼 1개만 (UI-DESIGN §8-1) */}
        <Button onClick={() => setFormOpen(true)}>
          <PlusIcon />
          업무 추가
        </Button>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        {COLUMN_ORDER.map((status) => {
          const col = columns[status];
          const remaining = col.total - col.items.length;
          const firstLoad = col.loading && col.page === 0;

          return (
            <section
              key={status}
              aria-label={STATUSES[status].label}
              className="flex flex-col gap-3 rounded-lg bg-neutral-100 p-3"
            >
              <h2 className="flex items-center gap-2 px-1 font-semibold">
                <span
                  className={`size-2 rounded-full ${STATUSES[status].dot}`}
                />
                {STATUSES[status].label}
                <span className="text-neutral-400">{col.total}</span>
              </h2>

              {firstLoad ? (
                <SkeletonList count={2} />
              ) : col.items.length === 0 ? (
                <EmptyState
                  variant="column"
                  title={EMPTY_TEXT[status]}
                  description="카드의 상태를 바꾸면 여기로 옮겨집니다"
                />
              ) : (
                <ul className="flex flex-col gap-2">
                  {col.items.map((task) => (
                    <li key={task.id}>
                      <TaskCard
                        task={task}
                        canChangeStatus={canChangeStatus(
                          task,
                          project.my_role,
                          me.id,
                        )}
                        updating={updatingId === task.id}
                        onStatusChange={(next) => changeStatus(task, next)}
                        onOpen={() => navigate(`tasks/${task.id}`)}
                      />
                    </li>
                  ))}
                </ul>
              )}

              {remaining > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  loading={col.loading}
                  onClick={() => loadMore(status)}
                >
                  {remaining}개 더 보기
                  <ChevronDownIcon />
                </Button>
              )}
            </section>
          );
        })}
      </div>

      {/* 새 업무는 항상 TODO로 만들어지므로 '할 일' 컬럼만 다시 불러온다. */}
      {formOpen && (
        <TaskFormModal
          members={members}
          onMembersStale={loadMembers}
          onClose={() => setFormOpen(false)}
          onCreated={() => {
            setFormOpen(false);
            loadColumn("TODO");
          }}
        />
      )}

      {/* 업무 상세 모달(S6)이 보드 위에 열린다 — /projects/:id/tasks/:taskId */}
      <Outlet />
    </div>
  );
}
