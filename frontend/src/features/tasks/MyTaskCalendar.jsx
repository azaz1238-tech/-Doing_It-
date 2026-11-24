import { useState } from "react";
import { Link } from "react-router";
import Button from "../../core/ui/Button";
import { ChevronLeftIcon, ChevronRightIcon } from "../../core/ui/icons";
import { cn } from "../../core/utils/cn";
import {
  WEEKDAYS,
  addDays,
  daysBetween,
  todayKst,
  weekdayOf,
} from "../../core/utils/date";
import PriorityBadge from "./PriorityBadge";

// 내 대시보드 위쪽 월간 달력 — TASK-11 · US-30 · SPEC-CHANGELOG #32 (P2, 기능 동결 예외)
// 내 대시보드가 받은 `GET /users/me/tasks` 응답(내 미완료 업무)을 그대로 받아 마감일 칸에 그린다. 따로 호출하지 않는다.
// 마감일 없는 업무는 달력에 그리지 않는다(아래 목록에만 나옴). 날짜는 "YYYY-MM-DD" 문자열로만 계산한다(core/utils/date).

// 지연·임박 강조는 서버가 준 alert를 그대로 쓴다(아래 목록과 같은 기준). 전체 클래스 이름을 적는다(Tailwind).
// 색만으로 알리지 않도록 화면 읽기 프로그램용 글자(label)도 함께 둔다.
const ALERTS = {
  OVERDUE: { border: "border-l-danger", label: "지연" },
  DUE_SOON: { border: "border-l-warning", label: "임박" },
};

// "YYYY-MM-01" (month는 1~12, 범위를 넘으면 해를 넘긴다)
function monthStart(year, month) {
  const y = year + Math.floor((month - 1) / 12);
  const m = ((((month - 1) % 12) + 12) % 12) + 1;
  return `${y}-${String(m).padStart(2, "0")}-01`;
}

// 그 달을 덮는 일요일 시작 주들의 날짜 목록 (4~6주)
function monthCells(first, next) {
  const lead = weekdayOf(first);
  const days = daysBetween(first, next);
  const weeks = Math.ceil((lead + days) / 7);
  const start = addDays(first, -lead);
  return Array.from({ length: weeks * 7 }, (_, i) => addDays(start, i));
}

/**
 * @param {Array} tasks MyTask 목록 (`due_date`, `alert`, `priority`, `title`, `project.id`)
 * @param {number} total 서버가 알려 준 내 미완료 업무 전체 개수 (받은 개수보다 많으면 일부만 그렸다고 알린다)
 */
export default function MyTaskCalendar({ tasks, total }) {
  const today = todayKst();
  const [todayYear, todayMonth] = today.split("-").map(Number);
  const [view, setView] = useState({ year: todayYear, month: todayMonth });

  const first = monthStart(view.year, view.month);
  const next = monthStart(view.year, view.month + 1);
  const cells = monthCells(first, next);

  // 마감일별로 묶는다. 서버 순서(지연 → 임박 → 나머지, 마감일 순)를 그대로 둔다.
  const byDate = new Map();
  let noDueCount = 0;
  for (const task of tasks) {
    if (!task.due_date) {
      noDueCount += 1;
      continue;
    }
    if (!byDate.has(task.due_date)) byDate.set(task.due_date, []);
    byDate.get(task.due_date).push(task);
  }

  const move = (delta) =>
    setView(({ year, month }) => {
      const [y, m] = monthStart(year, month + delta)
        .split("-")
        .map(Number);
      return { year: y, month: m };
    });

  return (
    <section
      aria-label="마감일 달력"
      className="overflow-hidden rounded-xl border border-neutral-200 bg-white"
    >
      <div className="flex items-center gap-2 border-b border-neutral-200 px-4 py-3">
        <Button
          variant="secondary"
          size="sm"
          className="px-2"
          onClick={() => move(-1)}
          aria-label="이전 달"
        >
          <ChevronLeftIcon />
        </Button>
        <h2
          aria-live="polite"
          className="min-w-28 text-center text-base font-bold whitespace-nowrap text-neutral-900 tabular-nums"
        >
          {view.year}년 {view.month}월
        </h2>
        <Button
          variant="secondary"
          size="sm"
          className="px-2"
          onClick={() => move(1)}
          aria-label="다음 달"
        >
          <ChevronRightIcon />
        </Button>
        <Button
          variant="secondary"
          size="sm"
          className="ml-auto"
          onClick={() => setView({ year: todayYear, month: todayMonth })}
        >
          오늘
        </Button>
      </div>

      <div className="grid grid-cols-7">
        {WEEKDAYS.map((name, i) => (
          <div
            key={name}
            className={cn(
              "border-b border-neutral-200 px-2 py-1.5 text-xs font-semibold",
              // 날짜 칸과 같은 위치에 세로선 (토요일 오른쪽은 표 테두리라 뺀다)
              i !== 6 && "border-r",
              i === 0
                ? "text-danger"
                : i === 6
                  ? "text-primary"
                  : "text-neutral-500",
            )}
          >
            {name}
          </div>
        ))}

        {cells.map((date, i) => {
          const inMonth = date >= first && date < next;
          const isToday = date === today;
          const dayTasks = byDate.get(date) ?? [];
          return (
            <div
              key={date}
              className={cn(
                "flex min-h-24 min-w-0 flex-col gap-1 border-b border-neutral-200 p-1",
                i % 7 !== 6 && "border-r",
                !inMonth && "bg-neutral-50",
              )}
            >
              <span
                className={cn(
                  "self-start px-1.5 py-0.5 text-xs font-semibold tabular-nums",
                  isToday
                    ? "min-w-6 rounded-full bg-primary text-center text-white"
                    : inMonth
                      ? "text-neutral-600"
                      : "text-neutral-400",
                )}
              >
                {Number(date.slice(8))}
                {isToday && <span className="sr-only"> 오늘</span>}
              </span>
              {dayTasks.map((task) => (
                <CalendarTask key={task.id} task={task} />
              ))}
            </div>
          );
        })}
      </div>

      {/* 달력에 안 나오는 업무 안내 — 마감일 없음(TASK-11-a), 100건 넘음(API-SPEC §8) */}
      {(noDueCount > 0 || total > tasks.length) && (
        <div className="flex flex-col gap-1 px-4 py-2.5 text-sm text-neutral-500">
          {noDueCount > 0 && (
            <p>마감일 없는 업무 {noDueCount}개는 아래 목록에 있습니다</p>
          )}
          {total > tasks.length && (
            <p className="text-warning">
              업무가 많아 {tasks.length}개까지만 달력에 표시합니다
            </p>
          )}
        </div>
      )}
    </section>
  );
}

// 칸 안의 업무 한 줄: 우선순위 배지 + 제목. 누르면 그 프로젝트 칸반 위에 업무 상세(S6).
// 제목·프로젝트 이름은 JSX 글자로만 넣는다(dangerouslySetInnerHTML 금지).
function CalendarTask({ task }) {
  const alert = ALERTS[task.alert];
  return (
    <Link
      to={`/projects/${task.project.id}/tasks/${task.id}`}
      title={`${task.title} · ${task.project.name}`}
      className={cn(
        "flex min-w-0 items-center gap-1 rounded-md border border-l-4 border-neutral-200 bg-white px-1 py-0.5 text-xs hover:bg-neutral-50",
        "focus-visible:outline-2 focus-visible:outline-primary",
        alert?.border ?? "border-l-neutral-300",
      )}
    >
      <PriorityBadge priority={task.priority} className="shrink-0" />
      {alert && <span className="sr-only">{alert.label}</span>}
      <span className="min-w-0 truncate font-medium text-neutral-900">
        {task.title}
      </span>
    </Link>
  );
}
