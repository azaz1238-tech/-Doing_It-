import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import Button from "../../core/ui/Button";
import EmptyState from "../../core/ui/EmptyState";
import { CheckIcon, ClockIcon, TriangleAlertIcon } from "../../core/ui/icons";
import Skeleton from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import { listMyTasks } from "./api";
import DueLabel from "./DueLabel";
import MyTaskCalendar from "./MyTaskCalendar";
import PriorityBadge from "./PriorityBadge";
import { STATUSES } from "./taskDisplay";

// 내 대시보드 `/` — DASH-04 · US-23 · REQUIREMENTS §6 (P1, T-F5-08)
// 나에게 할당된 미완료 업무를 프로젝트 구분 없이 보여 준다. 정렬은 서버 순서 그대로(지연 → 임박 → 나머지, 마감일 순).
// 지연·임박은 맨 위에 그룹 제목 색으로 강조한다(DASH-04-a). 그룹은 서버가 준 alert로 나눈다(화면에서 날짜를 다시 계산하지 않음).
// 목록 위에 월간 달력(TASK-11, P2)을 둔다. 할당 업무가 없으면 달력 없이 빈 상태만 보인다(DASH-04-b).

// TODO(Figma): 그룹 제목·색은 시안 확정 전 추정값
const GROUPS = [
  {
    alert: "OVERDUE",
    title: "지연",
    icon: TriangleAlertIcon,
    titleClass: "text-danger",
  },
  {
    alert: "DUE_SOON",
    title: "임박",
    icon: ClockIcon,
    titleClass: "text-warning",
  },
  { alert: null, title: "그 밖의 업무", titleClass: "text-neutral-700" },
];

export default function MyDashboardPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [data, setData] = useState(null); // null = 불러오는 중
  const [loadFailed, setLoadFailed] = useState(false);

  // 처음 그릴 때 data=null(불러오는 중)이라 effect 안에서는 응답만 기다린다(S3 목록과 같은 방식).
  const fetchTasks = useCallback(
    () =>
      listMyTasks()
        .then(setData)
        .catch((error) => {
          setLoadFailed(true);
          toast.error(
            error.response?.data?.message ?? "잠시 후 다시 시도해 주세요",
          );
        }),
    [toast],
  );

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const retry = () => {
    setLoadFailed(false);
    setData(null);
    fetchTasks();
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="flex items-center gap-2 whitespace-nowrap text-2xl font-bold text-neutral-900">
        내 업무
        {data && (
          <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-sm font-semibold text-neutral-600">
            {data.total}
          </span>
        )}
      </h1>

      {loadFailed ? (
        <div className="flex flex-col items-center gap-3 py-16 text-neutral-500">
          <p>내 업무를 불러오지 못했습니다</p>
          <Button variant="secondary" onClick={retry}>
            다시 시도
          </Button>
        </div>
      ) : data === null ? (
        <div role="status" aria-live="polite" className="flex flex-col gap-3">
          <span className="sr-only">불러오는 중입니다</span>
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : data.items.length === 0 ? (
        // DASH-04-b
        <EmptyState
          icon={CheckIcon}
          title="할당된 업무가 없습니다"
          description="프로젝트에서 업무를 확인해 보세요"
          action={
            <Button onClick={() => navigate("/projects")}>
              프로젝트로 가기
            </Button>
          }
        />
      ) : (
        <>
          {/* TASK-11: 위쪽 월간 달력, 아래는 DASH-04 목록 그대로 (같은 응답을 함께 쓴다) */}
          <MyTaskCalendar tasks={data.items} total={data.total} />
          {GROUPS.map((group) => {
            const tasks = data.items.filter((t) => t.alert === group.alert);
            // 비어 있는 그룹은 제목까지 숨긴다
            if (tasks.length === 0) return null;
            return <TaskGroup key={group.title} group={group} tasks={tasks} />;
          })}
        </>
      )}
    </div>
  );
}

function TaskGroup({ group, tasks }) {
  const Icon = group.icon;
  return (
    <section className="flex flex-col gap-2">
      <h2
        className={cn(
          "flex items-center gap-1.5 text-sm font-bold",
          group.titleClass,
        )}
      >
        {Icon && <Icon size={14} />}
        {group.title}
        <span className="rounded-md bg-neutral-100 px-1.5 text-xs font-semibold text-neutral-600">
          {tasks.length}
        </span>
      </h2>
      <ul className="divide-y divide-neutral-200 rounded-xl border border-neutral-200 bg-white px-4">
        {tasks.map((task) => (
          <li key={task.id}>
            <TaskRow task={task} />
          </li>
        ))}
      </ul>
    </section>
  );
}

// 한 줄: 우선순위 · 제목 · 프로젝트 이름 · 상태 · 마감. 담당자는 항상 나라서 아바타는 넣지 않는다. 누르면 그 프로젝트 칸반 위에 업무 상세(S6).
// 제목·프로젝트 이름은 JSX 글자로만 넣는다(dangerouslySetInnerHTML 금지).
function TaskRow({ task }) {
  const status = STATUSES[task.status];
  return (
    <Link
      to={`/projects/${task.project.id}/tasks/${task.id}`}
      className="-mx-2 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-2 py-3 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-primary sm:flex-nowrap"
    >
      <PriorityBadge priority={task.priority} className="shrink-0" />
      <span className="min-w-0 flex-1 truncate font-medium text-neutral-900">
        {task.title}
      </span>
      {/* 모바일에서는 아래 줄로 내려간다 */}
      <span className="flex w-full items-center gap-3 sm:w-auto sm:shrink-0">
        <span className="min-w-0 max-w-40 truncate text-sm text-neutral-500">
          {task.project.name}
        </span>
        {status && (
          <span className="flex shrink-0 items-center gap-1.5 text-xs text-neutral-600">
            <span className={cn("size-2 rounded-full", status.dot)} />
            {status.label}
          </span>
        )}
        <span className="ml-auto sm:ml-0">
          <DueLabel dueDate={task.due_date} status={task.status} />
        </span>
      </span>
    </Link>
  );
}
