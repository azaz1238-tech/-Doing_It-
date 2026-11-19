import { useCallback, useEffect, useRef, useState } from "react";
import {
  Outlet,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router";
import { useAuth } from "../../core/auth/useAuth";
import Button from "../../core/ui/Button";
import EmptyState from "../../core/ui/EmptyState";
import ErrorPage from "../../core/ui/ErrorPage";
import { ChevronDownIcon, PlusIcon } from "../../core/ui/icons";
import { SkeletonList } from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { getProject, listMembers } from "../projects/api";
import ProjectHeader from "../projects/ProjectHeader";
import { listTasks, updateTask } from "./api";
import { canChangeStatus } from "./permissions";
import FilterBar from "./FilterBar";
import TaskCard from "./TaskCard";
import TaskFormModal from "./TaskFormModal";
import { STATUSES } from "./taskDisplay";

// S4 칸반 보드 — UI-DESIGN §4 S4, TASK-02·TASK-05, PRJ-07.
// 데이터: 프로젝트 1번(GET /projects/{id}) + 컬럼마다 GET /projects/{id}/tasks?status=…&size=20

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

// 검색·필터(TASK-07) — URL 쿼리 이름은 API 쿼리와 같다(API-SPEC §5.4). 새로고침·링크 공유해도 같은 화면.
const FILTER_KEYS = ["q", "assignee_id", "priority", "due_from", "due_to"];
const readFilters = (params) =>
  Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) ?? ""]));
// 빈 조건은 보내지 않는다
const queryOf = (filterKey) =>
  Object.fromEntries(
    filterKey
      .split("|")
      .map((v, i) => [FILTER_KEYS[i], v])
      .filter(([, v]) => v !== ""),
  );

// 페이지 진입 오류는 안내 화면으로 바꾼다(UI-DESIGN S8). 그 밖의 오류는 null → 토스트.
function pageErrorOf(error) {
  const res = error.response;
  if (res?.data?.code === "NOT_PROJECT_MEMBER") return "403";
  // 프로젝트가 없을 때만 404 화면. 그 밖의 404(예: 업무 없음)는 토스트로 보여 준다.
  if (res?.data?.code === "PROJECT_NOT_FOUND") return "404";
  return null;
}

// 프로젝트가 바뀌면 상태를 모두 새로 시작하도록 id를 key로 준다(/projects/1 → /projects/2).
export default function BoardPage() {
  const { id } = useParams();
  // 주소의 id가 숫자가 아니면(/projects/abc) 서버가 422를 줘 스켈레톤만 남는다 → 바로 404 안내(최진영 #53 제보).
  if (!/^\d+$/.test(id))
    return <ErrorPage type="404" title="프로젝트를 찾을 수 없습니다" />;
  return <Board key={id} projectId={id} />;
}

function Board({ projectId }) {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = readFilters(searchParams);
  const filterActive = FILTER_KEYS.some((k) => filters[k] !== "");
  // useCallback 의존값으로 쓰기 위한 문자열(필터가 실제로 바뀔 때만 컬럼을 다시 부른다)
  const filterKey = FILTER_KEYS.map((k) => filters[k]).join("|");

  const [project, setProject] = useState(null);
  const [pageError, setPageError] = useState(null); // "403" | "404" | null
  const [columns, setColumns] = useState(() =>
    Object.fromEntries(COLUMN_ORDER.map((s) => [s, emptyColumn()])),
  );
  const [updatingId, setUpdatingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  // 컬럼마다 마지막 요청 번호. 늦게 도착한 옛 응답이 새 응답을 덮지 않게 한다.
  const requestSeq = useRef({});

  // 멤버 목록 — 헤더 아바타 묶음(§3.2)과 담당자 선택지(S5·S6)가 같이 쓴다. 보드에서 한 번 받아 넘긴다.
  const [members, setMembers] = useState([]);

  const showError = useCallback(
    (error, fallback) => {
      const kind = pageErrorOf(error);
      if (kind) setPageError(kind);
      // 모르는 code는 서버 message를 그대로 보여 준다(UI-DESIGN §6.5).
      else toast.error(error.response?.data?.message ?? fallback);
    },
    [toast],
  );

  const patchColumn = (status, patch) =>
    setColumns((prev) => ({
      ...prev,
      [status]: { ...prev[status], ...patch },
    }));

  const nextSeq = (status) => {
    requestSeq.current[status] = (requestSeq.current[status] ?? 0) + 1;
    return requestSeq.current[status];
  };

  // 컬럼 하나를 첫 페이지부터 다시 불러온다.
  const loadColumn = useCallback(
    async (status) => {
      const seq = nextSeq(status);
      patchColumn(status, { loading: true });
      try {
        const data = await listTasks(projectId, {
          ...queryOf(filterKey),
          status,
          page: 1,
          size: PAGE_SIZE,
        });
        if (requestSeq.current[status] !== seq) return;
        patchColumn(status, {
          items: data.items,
          total: data.total,
          page: 1,
          loading: false,
        });
      } catch (error) {
        if (requestSeq.current[status] !== seq) return;
        patchColumn(status, { loading: false });
        showError(error, "업무 목록을 불러오지 못했습니다");
      }
    },
    [projectId, showError, filterKey],
  );

  // 프로젝트·멤버는 처음 한 번, 컬럼은 필터가 바뀔 때마다 다시 부른다.
  useEffect(() => {
    let ignore = false;
    getProject(projectId)
      .then((data) => !ignore && setProject(data))
      .catch(
        (error) =>
          !ignore && showError(error, "프로젝트를 불러오지 못했습니다"),
      );
    listMembers(projectId)
      .then((data) => !ignore && setMembers(data.items))
      .catch(
        (error) =>
          !ignore && showError(error, "멤버 목록을 불러오지 못했습니다"),
      );
    return () => {
      ignore = true;
    };
  }, [projectId, showError]);

  useEffect(() => {
    COLUMN_ORDER.forEach(loadColumn);
  }, [loadColumn]);

  // 필터 바꾸기 — 빈 값은 주소에서 지운다. 상세 모달 주소(tasks/:id)는 그대로 둔다.
  const changeFilters = (patch) =>
    setSearchParams(
      () => {
        // 연달아 바꿔도(시작일 → 끝일) 앞 변경이 사라지지 않게 항상 지금 주소에서 계산한다.
        const next = new URLSearchParams(window.location.search);
        for (const [k, v] of Object.entries(patch)) {
          if (v) next.set(k, v);
          else next.delete(k);
        }
        return next;
      },
      { replace: true },
    );
  const resetFilters = () => setSearchParams({}, { replace: true });

  // 등록 중 400 ASSIGNEE_NOT_MEMBER(그 사이 멤버가 빠짐) → 멤버 목록을 새로 받는다(UI-DESIGN S5).
  const reloadMembers = () =>
    listMembers(projectId).then(
      (data) => setMembers(data.items),
      () => {},
    );

  // 업무 수가 바뀌는 동작 뒤 → 프로젝트를 다시 받아 헤더 진행률을 갱신한다(DASH-01, T-F5-02).
  // 실패해도 보드는 그대로 쓸 수 있으니 안내 없이 이전 값을 둔다.
  const reloadProject = () =>
    getProject(projectId).then(
      (data) => setProject(data),
      () => {},
    );

  // "n개 더 보기": 다음 page를 불러와 이어 붙인다.
  const loadMore = async (status) => {
    const col = columns[status];
    const seq = nextSeq(status);
    patchColumn(status, { loading: true });
    try {
      const data = await listTasks(projectId, {
        ...queryOf(filterKey),
        status,
        page: col.page + 1,
        size: PAGE_SIZE,
      });
      if (requestSeq.current[status] !== seq) return;
      setColumns((prev) => ({
        ...prev,
        [status]: {
          items: [...prev[status].items, ...data.items],
          total: data.total,
          page: data.page,
          loading: false,
        },
      }));
    } catch (error) {
      if (requestSeq.current[status] !== seq) return;
      patchColumn(status, { loading: false });
      showError(error, "업무 목록을 불러오지 못했습니다");
    }
  };

  // 상태 변경 성공 → 바뀐 두 컬럼만 다시 조회 → 성공 토스트 (UI-DESIGN S4, TASK-02)
  const changeStatus = async (task, nextStatus) => {
    // 요청 전 상태를 따로 잡아 둔다(응답 뒤 task 값에 기대지 않는다).
    const prevStatus = task.status;
    setUpdatingId(task.id);
    try {
      await updateTask(task.id, { status: nextStatus });
      await Promise.all([loadColumn(prevStatus), loadColumn(nextStatus)]);
      reloadProject();
      toast.success(
        `상태를 '${STATUSES[nextStatus].label}'${TO_PARTICLE[nextStatus]} 변경했습니다`,
      );
    } catch (error) {
      const code = error.response?.data?.code;
      if (code === "FORBIDDEN") {
        // 버튼 동작의 403은 토스트만, 화면은 유지(UI-DESIGN S8). 문구는 SPEC TASK-08-b
        toast.error("상태를 바꿀 권한이 없습니다");
        // 그 사이 담당이 바뀐 경우 — 컬럼을 새로 받아 카드가 🔒로 보이게 한다.
        loadColumn(prevStatus);
      } else if (code === "TASK_NOT_FOUND") {
        // 그 사이 다른 사람이 지운 업무 — 안내 후 원래 컬럼을 새로 고친다.
        toast.error(error.response.data.message);
        loadColumn(prevStatus);
        reloadProject(); // 업무 수가 바뀌었으니 진행률도(#85 리뷰)
      } else {
        showError(error, "상태를 바꾸지 못했습니다");
      }
    } finally {
      setUpdatingId(null);
    }
  };

  // S8 안내 화면. PRJ-07-a: 비멤버에게는 프로젝트 이름도 보이지 않는다(헤더를 그리지 않음).
  if (pageError === "403") return <ErrorPage type="403" />;
  if (pageError === "404")
    return <ErrorPage type="404" title="프로젝트를 찾을 수 없습니다" />;

  return (
    <div className="flex flex-col gap-5">
      {/* UI-DESIGN §3.2 (최진영 ProjectHeader, COMPONENTS §3.14) */}
      <ProjectHeader
        project={project}
        members={members}
        active="board"
        actions={
          // + 업무 추가는 헤더 오른쪽 버튼 1개만 (UI-DESIGN §8-1)
          <Button onClick={() => setFormOpen(true)} disabled={!project}>
            <PlusIcon />
            업무 추가
          </Button>
        }
      />

      <FilterBar
        filters={filters}
        members={members}
        onChange={changeFilters}
        onReset={resetFilters}
        active={filterActive}
      />

      {/* TASK-07-c: 조건에 맞는 업무가 하나도 없으면 컬럼 대신 안내 + 초기화 */}
      {filterActive &&
      COLUMN_ORDER.every(
        (s) => !columns[s].loading && columns[s].total === 0,
      ) ? (
        <EmptyState
          title="조건에 맞는 업무가 없습니다"
          action={<Button onClick={resetFilters}>필터 초기화</Button>}
        />
      ) : (
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
                          // 프로젝트(내 역할)를 받기 전에는 잠가 둔다.
                          canChangeStatus={
                            !!project &&
                            !!user &&
                            canChangeStatus(task, project.my_role, user.id)
                          }
                          updating={updatingId === task.id}
                          onStatusChange={(next) => changeStatus(task, next)}
                          // 상세를 열어도 필터(주소 쿼리)는 그대로 둔다
                          onOpen={() =>
                            navigate({
                              pathname: `tasks/${task.id}`,
                              search: location.search,
                            })
                          }
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
      )}

      {/* 새 업무는 항상 TODO로 만들어지므로 '할 일' 컬럼만 다시 불러온다. */}
      {formOpen && (
        <TaskFormModal
          projectId={projectId}
          members={members}
          onMembersStale={reloadMembers}
          onClose={() => setFormOpen(false)}
          onCreated={() => {
            setFormOpen(false);
            loadColumn("TODO");
            reloadProject();
          }}
        />
      )}

      {/* 업무 상세 모달(S6)이 보드 위에 열린다 — /projects/:id/tasks/:taskId */}
      <Outlet
        context={{
          projectId,
          project,
          members,
          user,
          // 상세에서 바꾸면 어느 컬럼이 바뀌었는지 몰라도 되게 세 컬럼을 다시 불러온다.
          onTaskChanged: () => {
            COLUMN_ORDER.forEach(loadColumn);
            reloadProject();
          },
        }}
      />
    </div>
  );
}
