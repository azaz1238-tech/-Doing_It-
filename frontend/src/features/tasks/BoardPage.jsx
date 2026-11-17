import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, Outlet, useNavigate, useParams } from "react-router";
import { useAuth } from "../../core/auth/useAuth";
import Button from "../../core/ui/Button";
import EmptyState from "../../core/ui/EmptyState";
import {
  ChevronDownIcon,
  FolderIcon,
  LockIcon,
  PlusIcon,
} from "../../core/ui/icons";
import Skeleton, { SkeletonList } from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { formatPeriod } from "../../core/utils/date";
import { getProject } from "../projects/api";
import { listTasks, updateTask } from "./api";
import { canChangeStatus } from "./permissions";
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

// 페이지 진입 오류는 안내 화면으로 바꾼다(UI-DESIGN S8). 그 밖의 오류는 null → 토스트.
function pageErrorOf(error) {
  const res = error.response;
  if (res?.data?.code === "NOT_PROJECT_MEMBER") return "403";
  if (res?.status === 404) return "404";
  return null;
}

// 프로젝트가 바뀌면 상태를 모두 새로 시작하도록 id를 key로 준다(/projects/1 → /projects/2).
export default function BoardPage() {
  const { id } = useParams();
  return <Board key={id} projectId={id} />;
}

function Board({ projectId }) {
  const navigate = useNavigate();
  const toast = useToast();
  const { user } = useAuth();

  const [project, setProject] = useState(null);
  const [pageError, setPageError] = useState(null); // "403" | "404" | null
  const [columns, setColumns] = useState(() =>
    Object.fromEntries(COLUMN_ORDER.map((s) => [s, emptyColumn()])),
  );
  const [updatingId, setUpdatingId] = useState(null);
  const [formOpen, setFormOpen] = useState(false);
  // 컬럼마다 마지막 요청 번호. 늦게 도착한 옛 응답이 새 응답을 덮지 않게 한다.
  const requestSeq = useRef({});

  // 담당자 선택지(S5). TODO(T-F3-02): 멤버 목록 API(양준석, 11/18)가 나오면
  // features/projects/api.js의 listMembers로 바꾼다. 그전에는 확실히 멤버인 "나"만 둔다
  // (목 멤버를 두면 DB에 없는 사용자 id를 보내게 된다).
  const members = useMemo(
    () =>
      user
        ? [{ user_id: user.id, login_id: user.login_id, name: user.name }]
        : [],
    [user],
  );

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
    [projectId, showError],
  );

  useEffect(() => {
    let ignore = false;
    getProject(projectId)
      .then((data) => !ignore && setProject(data))
      .catch(
        (error) =>
          !ignore && showError(error, "프로젝트를 불러오지 못했습니다"),
      );
    COLUMN_ORDER.forEach(loadColumn);
    return () => {
      ignore = true;
    };
  }, [projectId, loadColumn, showError]);

  // "n개 더 보기": 다음 page를 불러와 이어 붙인다.
  const loadMore = async (status) => {
    const col = columns[status];
    const seq = nextSeq(status);
    patchColumn(status, { loading: true });
    try {
      const data = await listTasks(projectId, {
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
      } else {
        showError(error, "상태를 바꾸지 못했습니다");
      }
    } finally {
      setUpdatingId(null);
    }
  };

  // TODO(T-F0-14): ErrorPage(S8, 11/18)가 나오면 교체한다.
  if (pageError) {
    const forbidden = pageError === "403";
    return (
      <EmptyState
        icon={forbidden ? LockIcon : FolderIcon}
        // PRJ-07-a: 비멤버에게는 프로젝트 이름도 보이지 않는다.
        title={
          forbidden ? "접근 권한이 없습니다" : "프로젝트를 찾을 수 없습니다"
        }
        description={
          forbidden
            ? "이 프로젝트의 멤버만 볼 수 있습니다"
            : "삭제되었거나 주소가 올바르지 않습니다"
        }
        action={
          <Link
            to="/projects"
            className="inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-white hover:bg-primary-hover"
          >
            프로젝트 목록으로
          </Link>
        }
      />
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {/* TODO(최진영 ProjectHeader, 11/18 오전): UI-DESIGN §3.2 헤더로 교체. '업무 추가'는 BoardPage에 둔다 */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        {project ? (
          <div>
            <p className="text-xs text-neutral-500">프로젝트 ›</p>
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <p className="mt-1 text-xs text-neutral-500">
              {/* 시작일·종료일은 선택 항목이라 없을 수 있다. S3 카드와 같게 "기간 없음" */}
              {formatPeriod(project.start_date, project.end_date) ||
                "기간 없음"}
            </p>
          </div>
        ) : (
          <div aria-hidden="true" className="flex flex-col gap-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-7 w-48" />
            <Skeleton className="h-3 w-24" />
          </div>
        )}
        {/* + 업무 추가는 헤더 오른쪽 버튼 1개만 (UI-DESIGN §8-1) */}
        <Button onClick={() => setFormOpen(true)} disabled={!project}>
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
                        // 프로젝트(내 역할)를 받기 전에는 잠가 둔다.
                        canChangeStatus={
                          !!project &&
                          !!user &&
                          canChangeStatus(task, project.my_role, user.id)
                        }
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
          projectId={projectId}
          members={members}
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
