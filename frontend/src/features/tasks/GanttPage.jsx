import { useCallback, useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate, useParams } from "react-router";
import { useAuth } from "../../core/auth/useAuth";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import EmptyState from "../../core/ui/EmptyState";
import ErrorPage from "../../core/ui/ErrorPage";
import { ChevronLeftIcon, ChevronRightIcon } from "../../core/ui/icons";
import Skeleton from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import {
  addDays,
  daysBetween,
  formatMonthDay,
  formatPeriod,
  todayKst,
  weekdayOf,
  WEEKDAYS,
} from "../../core/utils/date";
import { getProject, listMembers } from "../projects/api";
import ProjectHeader from "../projects/ProjectHeader";
import { listTasks } from "./api";
import PriorityBadge from "./PriorityBadge";
import { getDueInfo } from "./taskDisplay";

// 간트 보기 (P2) — TASK-12, UI-DESIGN §4 "간트 보기", `/projects/:id/gantt`
// - 새 API 없음: 업무 목록(GET /projects/{id}/tasks?size=100)을 page를 늘려 끝까지 받는다(API-SPEC §8).
// - 막대: 만든 날(created_at → 한국 날짜) ~ 마감일. 마감일이 만든 날보다 앞이면 마감일 하루짜리(TASK-12-b).
// - 색: 완료 = success(흐리게), 미완료 = getDueInfo().tone(보드 DueLabel과 같은 기준: 지연·임박·예정).
// - 날짜 축: 일요일 시작 4주. 처음엔 오늘이 든 주의 1주 전부터, ‹ ›는 1주씩.
// - 날짜는 "YYYY-MM-DD" 문자열 그대로 다룬다(core/utils/date, COMPONENTS §3.13).

const DAYS = 28;
const PAGE_SIZE = 100;

// Tailwind가 클래스를 찾을 수 있도록 전체 이름을 그대로 적는다(문자열 조합 금지).
const TONES = {
  overdue: { label: "지연", bar: "bg-danger" },
  soon: { label: "임박", bar: "bg-warning" },
  normal: { label: "예정", bar: "bg-primary" },
  done: { label: "완료", bar: "bg-success/50" },
};
const LEGEND = ["overdue", "soon", "normal", "done"];

// 날짜 칸 너비(데스크톱은 남는 폭을 나눠 쓴다)
const DAY_COLUMNS = {
  gridTemplateColumns: `repeat(${DAYS}, minmax(1.5rem, 1fr))`,
};
// 왼쪽 업무 칸(고정) + 날짜 축. 좁은 화면은 날짜 축만 상자 안에서 가로로 스크롤한다.
const ROW_GRID = "grid grid-cols-[8.5rem_1fr] sm:grid-cols-[15rem_1fr]";

/** 오늘이 든 주(일요일 시작)의 1주 전 일요일 */
const firstWindowStart = (today) => addDays(today, -weekdayOf(today) - 7);

// 페이지 진입 오류 → S8 안내 화면(통계·설정과 같은 기준). TASK-12-c: 비멤버는 안내만 본다.
function pageErrorOf(error) {
  const code = error.response?.data?.code;
  if (code === "NOT_PROJECT_MEMBER") return "403";
  if (code === "PROJECT_NOT_FOUND") return "404";
  return null;
}

/** 업무 목록을 끝까지 받는다(한 번에 최대 100건) */
async function listAllTasks(projectId) {
  const all = [];
  for (let page = 1; ; page += 1) {
    const data = await listTasks(projectId, { page, size: PAGE_SIZE });
    all.push(...data.items);
    if (all.length >= data.total || data.items.length === 0) return all;
  }
}

/** 막대 한 줄의 날짜·색 */
function toBar(task, today) {
  // created_at은 UTC("…Z")라 앞 10자리를 자르면 한국 00:00~08:59에 만든 업무가 하루 앞으로 간다 → 한국 날짜로 바꾼다
  const created = todayKst(Date.parse(task.created_at));
  const end = task.due_date;
  const start = created <= end ? created : end; // 마감일이 만든 날보다 앞이면 마감일 하루짜리
  const tone =
    task.status === "DONE" ? "done" : getDueInfo(task.due_date, today).tone;
  return { start, end, tone };
}

// 프로젝트가 바뀌면 상태를 모두 새로 시작하도록 id를 key로 준다(보드·통계와 같음).
export default function GanttPage() {
  const { id } = useParams();
  if (!/^\d+$/.test(id))
    return <ErrorPage type="404" title="프로젝트를 찾을 수 없습니다" />;
  return <Gantt key={id} projectId={id} />;
}

function Gantt({ projectId }) {
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();
  const { user } = useAuth();
  const today = todayKst();

  const [project, setProject] = useState(null);
  const [members, setMembers] = useState(null);
  const [pageError, setPageError] = useState(null); // "403" | "404" | null
  const [projectFailed, setProjectFailed] = useState(false);
  const [tasks, setTasks] = useState(null); // null = 불러오는 중
  const [tasksFailed, setTasksFailed] = useState(false);
  const [attempt, setAttempt] = useState(0); // 다시 시도하면 1 늘려 effect를 다시 돌린다
  const [windowStart, setWindowStart] = useState(() => firstWindowStart(today));

  const loadTasks = useCallback(
    () =>
      listAllTasks(projectId).then(
        (items) => {
          setTasks(items);
          setTasksFailed(false);
        },
        (error) => {
          const kind = pageErrorOf(error);
          if (kind) return setPageError(kind);
          setTasksFailed(true);
        },
      ),
    [projectId],
  );

  const loadProject = useCallback(
    () =>
      getProject(projectId).then(
        (data) => {
          setProject(data);
          setProjectFailed(false);
        },
        (error) => {
          const kind = pageErrorOf(error);
          if (kind) return setPageError(kind);
          setProjectFailed(true);
          toast.error(
            error.response?.data?.message ?? "프로젝트를 불러오지 못했습니다",
          );
        },
      ),
    [projectId, toast],
  );

  useEffect(() => {
    loadProject();
    // 헤더 아바타·상세 담당자 선택지용. 실패하면 아바타만 그리지 않는다.
    listMembers(projectId).then(
      (data) => setMembers(data.items),
      () => setMembers([]),
    );
    loadTasks();
  }, [projectId, loadProject, loadTasks, attempt]);

  const retry = () => {
    setProjectFailed(false);
    setTasksFailed(false);
    setTasks(null);
    setAttempt((n) => n + 1);
  };

  if (pageError === "403") return <ErrorPage type="403" />;
  if (pageError === "404")
    return <ErrorPage type="404" title="프로젝트를 찾을 수 없습니다" />;

  const windowEnd = addDays(windowStart, DAYS - 1);
  const days = Array.from({ length: DAYS }, (_, i) => addDays(windowStart, i));
  const todayIndex = daysBetween(windowStart, today);
  const atToday = windowStart === firstWindowStart(today);

  // 마감일 있는 업무만 막대로(마감일 빠른 순 → id). 마감일 없는 업무는 개수만(TASK-12-b).
  const rows = (tasks ?? [])
    .filter((t) => t.due_date)
    .sort((a, b) =>
      a.due_date === b.due_date
        ? a.id - b.id
        : a.due_date < b.due_date
          ? -1
          : 1,
    );
  const noDueCount = (tasks ?? []).filter((t) => !t.due_date).length;

  const openTask = (taskId) =>
    navigate({ pathname: `tasks/${taskId}`, search: location.search });

  return (
    <div className="flex flex-col gap-5">
      <ProjectHeader project={project} members={members} active="gantt" />

      {projectFailed || tasksFailed ? (
        <div className="flex flex-col items-center gap-3 py-12 text-sm text-neutral-500">
          <p>
            {projectFailed
              ? "프로젝트를 불러오지 못했습니다"
              : "업무를 불러오지 못했습니다"}
          </p>
          <Button variant="secondary" onClick={retry}>
            다시 시도
          </Button>
        </div>
      ) : (
        <>
          {/* 기간 이동 + 범례 */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1">
              <Button
                variant="secondary"
                size="sm"
                aria-label="이전 주"
                onClick={() => setWindowStart(addDays(windowStart, -7))}
              >
                <ChevronLeftIcon />
              </Button>
              <span
                aria-live="polite"
                className="min-w-28 text-center text-sm font-semibold text-neutral-900 tabular-nums"
              >
                {formatPeriod(windowStart, windowEnd)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                aria-label="다음 주"
                onClick={() => setWindowStart(addDays(windowStart, 7))}
              >
                <ChevronRightIcon />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={atToday}
                onClick={() => setWindowStart(firstWindowStart(today))}
              >
                오늘
              </Button>
            </div>
            <ul
              aria-label="막대 색"
              className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-neutral-600"
            >
              {LEGEND.map((tone) => (
                <li key={tone} className="flex items-center gap-1.5">
                  <span
                    aria-hidden="true"
                    className={cn("size-2.5 rounded-sm", TONES[tone].bar)}
                  />
                  {TONES[tone].label}
                </li>
              ))}
            </ul>
          </div>

          {tasks === null ? (
            <div aria-hidden="true" className="flex flex-col gap-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : rows.length === 0 ? (
            <EmptyState
              title="마감일이 있는 업무가 없습니다"
              description="업무에 마감일을 넣으면 간트에 막대로 보입니다"
            />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-neutral-200 bg-white">
              <div className="min-w-[44rem]">
                <DateAxis days={days} today={today} />
                <ul>
                  {rows.map((task) => (
                    <GanttRow
                      key={task.id}
                      task={task}
                      bar={toBar(task, today)}
                      windowStart={windowStart}
                      windowEnd={windowEnd}
                      days={days}
                      todayIndex={todayIndex}
                      onOpen={() => openTask(task.id)}
                    />
                  ))}
                </ul>
              </div>
            </div>
          )}

          {tasks !== null && noDueCount > 0 && (
            <p className="text-sm text-neutral-500">
              마감일 없는 업무 {noDueCount}개는 간트에 나오지 않습니다
            </p>
          )}
        </>
      )}

      {/* 업무 상세(S6)가 간트 위에 열린다 — /projects/:id/gantt/tasks/:taskId, 닫으면 간트로 */}
      <Outlet
        context={{
          projectId,
          project,
          members: members ?? [],
          user,
          basePath: `/projects/${projectId}/gantt`,
          // 상세에서 바꾸거나 지우면 막대·진행률을 다시 그린다
          onTaskChanged: () => {
            loadTasks();
            loadProject();
          },
        }}
      />
    </div>
  );
}

// 날짜 머리글: 요일 + 날짜. 첫 칸과 1일은 "11/1"처럼 월을 붙인다.
function DateAxis({ days, today }) {
  return (
    <div className={cn(ROW_GRID, "border-b border-neutral-200 text-xs")}>
      <div className="sticky left-0 z-10 flex items-end bg-white px-3 py-2 font-semibold text-neutral-500">
        업무
      </div>
      <div className="grid" style={DAY_COLUMNS}>
        {days.map((d, i) => {
          const weekend = weekdayOf(d) === 0 || weekdayOf(d) === 6;
          const isToday = d === today;
          const dayOfMonth = Number(d.slice(8));
          return (
            <div
              key={d}
              className={cn(
                "flex flex-col items-center py-1.5 leading-tight",
                weekend && "bg-neutral-50",
                isToday ? "font-bold text-primary" : "text-neutral-500",
              )}
            >
              <span aria-hidden="true">{WEEKDAYS[weekdayOf(d)]}</span>
              <span className="tabular-nums">
                {i === 0 || dayOfMonth === 1 ? formatMonthDay(d) : dayOfMonth}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GanttRow({
  task,
  bar,
  windowStart,
  windowEnd,
  days,
  todayIndex,
  onOpen,
}) {
  const { start, end, tone } = bar;
  const visible = end >= windowStart && start <= windowEnd;
  const from = start < windowStart ? windowStart : start;
  const to = end > windowEnd ? windowEnd : end;
  const left = (daysBetween(windowStart, from) / DAYS) * 100;
  const width = ((daysBetween(from, to) + 1) / DAYS) * 100;
  const period = `${formatMonthDay(start)} ~ ${formatMonthDay(end)}`;
  const label = `${task.title}, ${period}, ${TONES[tone].label}`;

  return (
    <li className={cn(ROW_GRID, "border-b border-neutral-100 last:border-b-0")}>
      {/* 왼쪽: 우선순위 · 제목 · 담당자 (가로 스크롤해도 고정).
          모바일은 배지·아바타를 숨겨 좁은 칸을 제목이 쓴다(통계 담당자 표와 같은 방식). 막대 색·상세에서 확인할 수 있다 */}
      <div className="sticky left-0 z-10 flex min-w-0 items-center gap-2 bg-white px-3 py-2">
        <span className="hidden shrink-0 sm:block">
          <PriorityBadge priority={task.priority} />
        </span>
        <button
          type="button"
          onClick={onOpen}
          title={task.title}
          className={cn(
            "min-w-0 flex-1 truncate text-left text-sm font-medium hover:text-primary",
            task.status === "DONE"
              ? "text-neutral-400 line-through"
              : "text-neutral-900",
          )}
        >
          {task.title}
        </button>
        <span className="hidden shrink-0 sm:block">
          <Avatar user={task.assignee} size="sm" />
        </span>
      </div>

      {/* 오른쪽: 날짜 축 위 막대 */}
      <div className="relative">
        <div
          aria-hidden="true"
          className="absolute inset-0 grid"
          style={DAY_COLUMNS}
        >
          {days.map((d) => (
            <div
              key={d}
              className={cn(
                "border-l border-neutral-100 first:border-l-0",
                (weekdayOf(d) === 0 || weekdayOf(d) === 6) && "bg-neutral-50",
              )}
            />
          ))}
        </div>
        {todayIndex >= 0 && todayIndex < DAYS && (
          <div
            aria-hidden="true"
            className="absolute inset-y-0 w-px bg-primary/60"
            style={{ left: `${((todayIndex + 0.5) / DAYS) * 100}%` }}
          />
        )}
        {visible ? (
          <button
            type="button"
            onClick={onOpen}
            aria-label={label}
            title={label}
            className={cn(
              "absolute top-1/2 h-5 -translate-y-1/2 rounded-full hover:brightness-95 focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary",
              TONES[tone].bar,
              start < windowStart && "rounded-l-none",
              end > windowEnd && "rounded-r-none",
            )}
            style={{ left: `${left}%`, width: `${width}%` }}
          />
        ) : (
          // 보이는 4주 밖 막대 — 어느 쪽에 있는지만 알린다
          <span
            className={cn(
              "absolute inset-y-0 flex items-center px-2 text-xs text-neutral-400",
              end < windowStart ? "left-0" : "right-0",
            )}
          >
            {end < windowStart
              ? `‹ ${formatMonthDay(end)} 마감`
              : `${formatMonthDay(start)} 시작 ›`}
          </span>
        )}
      </div>
    </li>
  );
}
