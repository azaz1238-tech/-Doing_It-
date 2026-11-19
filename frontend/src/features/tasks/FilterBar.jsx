import { useEffect, useRef } from "react";
import Button from "../../core/ui/Button";
import { ChevronDownIcon } from "../../core/ui/icons";
import Input from "../../core/ui/Input";
import { cn } from "../../core/utils/cn";
import { PRIORITIES } from "./taskDisplay";

// S4 칸반 검색·필터 바 — UI-DESIGN S4 "[검색 · 담당자 · 우선순위 · 마감일 · 초기화]", TASK-07 (P1)
// 상태 필터는 따로 두지 않는다 — 칸반 컬럼이 곧 상태다.
// 값은 BoardPage가 URL 쿼리에서 읽어 넘기고, 바꾸면 onChange로 URL을 고친다(새로고침·링크 공유 유지).

const PRIORITY_ORDER = ["URGENT", "HIGH", "MEDIUM", "LOW"]; // 칸반 정렬과 같은 순서
const SEARCH_DELAY_MS = 300;

/**
 * @param {{ q: string, assignee_id: string, priority: string, due_from: string, due_to: string }} filters
 * @param {Array<{user_id:number, login_id:string, name:string}>} members
 * @param {(patch: object) => void} onChange 바뀐 필터만 넘긴다(빈 문자열 = 조건 없음)
 * @param {() => void} onReset 필터 초기화
 * @param {boolean} active 조건이 하나라도 있으면 true → `필터 초기화` 버튼 표시
 */
export default function FilterBar({
  filters,
  members,
  onChange,
  onReset,
  active,
}) {
  // 검색어는 칠 때마다 요청하지 않도록 잠깐 기다렸다가 넘긴다.
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  const changeSearch = (value) => {
    clearTimeout(timer.current);
    timer.current = setTimeout(
      () => onChange({ q: value.trim() }),
      SEARCH_DELAY_MS,
    );
  };

  return (
    <div
      role="search"
      aria-label="업무 검색·필터"
      className="flex flex-wrap items-end gap-2 rounded-lg border border-neutral-200 bg-white p-3"
    >
      {/* 초기화하면 입력칸도 비워야 해서, 바깥 값(q)이 바뀌면 다시 그린다 */}
      <Input
        key={filters.q}
        aria-label="제목 검색"
        placeholder="제목 검색"
        defaultValue={filters.q}
        onChange={(e) => changeSearch(e.target.value)}
        className="min-w-44 flex-1"
      />
      <FilterSelect
        label="담당자"
        value={filters.assignee_id}
        onChange={(v) => onChange({ assignee_id: v })}
      >
        <option value="">담당자 전체</option>
        <option value="none">담당자 없음</option>
        {members.map((m) => (
          <option key={m.user_id} value={String(m.user_id)}>
            {m.name} ({m.login_id})
          </option>
        ))}
      </FilterSelect>
      <FilterSelect
        label="우선순위"
        value={filters.priority}
        onChange={(v) => onChange({ priority: v })}
      >
        <option value="">우선순위 전체</option>
        {PRIORITY_ORDER.map((key) => (
          <option key={key} value={key}>
            {PRIORITIES[key].label}
          </option>
        ))}
      </FilterSelect>
      <DateField
        label="마감일 시작"
        value={filters.due_from}
        onChange={(v) => onChange({ due_from: v })}
      />
      <span className="self-center text-neutral-400" aria-hidden="true">
        ~
      </span>
      <DateField
        label="마감일 끝"
        value={filters.due_to}
        onChange={(v) => onChange({ due_to: v })}
      />
      {active && (
        <Button variant="ghost" onClick={onReset} className="h-10">
          필터 초기화
        </Button>
      )}
    </div>
  );
}

function FilterSelect({ label, value, onChange, children }) {
  return (
    <span className="relative flex">
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "h-10 appearance-none rounded-lg border bg-white pr-9 pl-3 text-sm focus:outline-2 focus:-outline-offset-1 focus:outline-primary",
          // 조건이 걸린 칸은 테두리로 표시한다
          value
            ? "border-primary text-neutral-900"
            : "border-neutral-300 text-neutral-600",
        )}
      >
        {children}
      </select>
      <ChevronDownIcon className="pointer-events-none absolute inset-y-0 right-3 my-auto text-neutral-500" />
    </span>
  );
}

function DateField({ label, value, onChange }) {
  return (
    <input
      type="date"
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={cn(
        "h-10 rounded-lg border bg-white px-3 text-sm focus:outline-2 focus:-outline-offset-1 focus:outline-primary",
        value
          ? "border-primary text-neutral-900"
          : "border-neutral-300 text-neutral-600",
      )}
    />
  );
}
