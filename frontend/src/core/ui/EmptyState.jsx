import { cn } from "../utils/cn";

/**
 * EmptyState — UI-DESIGN §5, 동잇 UI 시안 v0.3 "빈 화면"
 * 규칙: 비어 있을 때 다음 행동을 — 아이콘 + 이유 + 할 수 있는 행동 한 가지.
 *
 * @param {"page"|"column"} [variant] page = 화면 가운데(S3 프로젝트 0개), column = 칸반 컬럼 안 점선 상자(S4)
 * @param {import("react").ComponentType} [icon] icons/index.jsx의 아이콘 (page에서만 표시)
 * @param {string} title 이유 한 줄 (예: "프로젝트가 없습니다")
 * @param {string} [description] 보조 설명
 * @param {import("react").ReactNode} [action] 버튼 하나 (선택)
 */
export default function EmptyState({
  variant = "page",
  icon: Icon,
  title,
  description,
  action,
  className,
}) {
  if (variant === "column") {
    return (
      <div
        className={cn(
          "rounded-lg border border-dashed border-neutral-300 px-4 py-8 text-center",
          className,
        )}
      >
        <p className="text-neutral-600">{title}</p>
        {description && (
          <p className="mt-1 text-xs text-neutral-400">{description}</p>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center px-4 py-16 text-center",
        className,
      )}
    >
      {Icon && (
        <div className="mb-5 flex size-16 items-center justify-center rounded-xl bg-primary-soft text-primary">
          <Icon size={28} />
        </div>
      )}
      <h2 className="text-base font-bold text-neutral-900">{title}</h2>
      {description && <p className="mt-1.5 text-neutral-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
