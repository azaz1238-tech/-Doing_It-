import { cn } from "../utils/cn";

/**
 * Skeleton — UI-DESIGN §5, 동잇 UI 시안 v0.3 "불러오는 중 · 스켈레톤"
 * 불러오는 동안 실제 내용 자리에 회색 막대를 보여 준다. 화면 읽기 프로그램에는 "불러오는 중"만 알린다.
 */

// 막대 하나. 크기는 className으로 정한다. 예: <Skeleton className="h-4 w-24" />
export default function Skeleton({ className }) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded bg-neutral-100", className)}
    />
  );
}

// 카드 모양 (시안: 짧은 줄 · 긴 줄 · 짧은 줄 + 오른쪽 아래 알약). S3 목록, S4 보드 카드 자리에 쓴다.
export function SkeletonCard({ className }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "rounded-lg border border-neutral-200 bg-white p-5",
        className,
      )}
    >
      <Skeleton className="h-3 w-20" />
      <Skeleton className="mt-4 h-3.5 w-3/4" />
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
    </div>
  );
}

/**
 * 카드 여러 장 + "불러오는 중" 알림
 * @param {number} [count] 카드 수 (기본 2, 시안)
 * @param {string} [className] 감싸는 요소 — 그리드는 화면에서 정한다. 예: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
 */
export function SkeletonList({ count = 2, className }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("grid gap-3", className)}
    >
      <span className="sr-only">불러오는 중입니다</span>
      {Array.from({ length: count }, (_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
