import { useId } from "react";
import { ChevronDownIcon } from "../../core/ui/icons";
import { cn } from "../../core/utils/cn";

/**
 * MemberSelect — UI-DESIGN §5: 첫 항목 `담당자 없음` + 멤버(이름·아이디). S5 등록, S6 상세에서 쓴다.
 * 선택지는 이 프로젝트 멤버만 보인다(TASK-03-a). 멤버 목록은 화면이 GET /projects/{id}/members로 받아 넘긴다.
 *
 * @param {Array<{user_id:number, login_id:string, name:string}>} members API-SPEC §4 Member
 * @param {number|null} value 선택한 user_id, 없으면 null
 * @param {(userId: number|null) => void} onChange
 * @param {string} [error] 오류 문구 (예: ASSIGNEE_NOT_MEMBER)
 */
export default function MemberSelect({
  label = "담당자",
  members,
  value,
  onChange,
  error,
  disabled = false,
  className,
}) {
  const id = useId();
  const messageId = `${id}-message`;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label htmlFor={id} className="font-semibold text-neutral-900">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          id={id}
          // 라벨을 숨긴 곳(S6 속성 목록)에서도 화면 낭독기가 이름을 읽게 한다.
          aria-label={label ? undefined : "담당자"}
          value={value ?? ""}
          disabled={disabled}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? messageId : undefined}
          onChange={(e) =>
            onChange(e.target.value === "" ? null : Number(e.target.value))
          }
          className={cn(
            "h-10 w-full appearance-none rounded-lg border bg-white pr-9 pl-3 text-sm text-neutral-900",
            "focus:outline-2 focus:-outline-offset-1 disabled:cursor-not-allowed disabled:bg-neutral-100",
            error
              ? "border-danger focus:outline-danger"
              : "border-neutral-300 focus:outline-primary",
          )}
        >
          <option value="">담당자 없음</option>
          {members.map((m) => (
            <option key={m.user_id} value={m.user_id}>
              {m.name} ({m.login_id})
            </option>
          ))}
        </select>
        <ChevronDownIcon className="pointer-events-none absolute inset-y-0 right-3 my-auto text-neutral-500" />
      </div>
      {error && (
        <p id={messageId} className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
