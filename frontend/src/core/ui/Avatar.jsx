import { cn } from "../utils/cn";

// 사용자별 고정 색 — 같은 사용자 id는 항상 같은 색이 된다.
// Tailwind가 클래스를 찾을 수 있도록 전체 이름을 그대로 적는다(문자열 조합 금지).
// 색은 index.css의 avatar-1~4 토큰(시안 v0.3)만 쓴다.
const COLORS = ["bg-avatar-1", "bg-avatar-2", "bg-avatar-3", "bg-avatar-4"];

const SIZES = {
  sm: "size-6 text-xs",
  md: "size-8 text-sm",
};

// 시안 v0.3: 한국 이름은 성을 뺀 이름 첫 글자(김민호 → 민). 같은 성이 많아 성으로는 구분이 안 된다.
// 한글 3자 이름만 둘째 글자를 쓰고, 그 밖(2자·4자·영문 등)은 첫 글자를 쓴다. 규칙은 김서현과 확인한다.
function getInitial(name) {
  const trimmed = name.trim();
  return /^[가-힣]{3}$/.test(trimmed) ? trimmed.charAt(1) : trimmed.charAt(0);
}

/**
 * Avatar — UI-DESIGN §5: 이름 첫 글자 + 사용자별 고정 색. 담당자 없음은 `?` 회색.
 * 표시 글자는 getInitial 규칙을 따른다 (김민호 → 민, Jisu → J).
 * @param {{ id: number, name: string } | null} user 없으면 "담당자 없음"
 */
export default function Avatar({ user, size = "md", className }) {
  const empty = !user;
  const color = empty ? "bg-neutral-300" : COLORS[user.id % COLORS.length];
  const initial = empty ? "?" : getInitial(user.name);

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
