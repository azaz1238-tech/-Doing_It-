import { cn } from "../utils/cn";

// 사용자별 고정 색 — 같은 사용자 id는 항상 같은 색이 된다.
// Tailwind가 클래스를 찾을 수 있도록 전체 이름을 그대로 적는다(문자열 조합 금지).
// 색은 index.css의 avatar-1~4 토큰(시안 v0.3)만 쓴다.
const COLORS = ["bg-avatar-1", "bg-avatar-2", "bg-avatar-3", "bg-avatar-4"];

const SIZES = {
  sm: "size-6 text-xs",
  md: "size-8 text-sm",
};

/**
 * Avatar — UI-DESIGN §5: 이름 첫 글자 + 사용자별 고정 색. 담당자 없음은 `?` 회색.
 * @param {{ id: number, name: string } | null} user 없으면 "담당자 없음"
 */
export default function Avatar({ user, size = "md", className }) {
  const empty = !user;
  const color = empty ? "bg-neutral-300" : COLORS[user.id % COLORS.length];
  const initial = empty ? "?" : user.name.trim().charAt(0);

  return (
    <span
      role="img"
      aria-label={empty ? "담당자 없음" : user.name}
      title={empty ? "담당자 없음" : user.name}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white select-none",
        color,
        SIZES[size],
        className,
      )}
    >
      {initial}
    </span>
  );
}
