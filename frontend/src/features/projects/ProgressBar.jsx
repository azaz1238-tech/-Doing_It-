import { cn } from "../../core/utils/cn";

/**
 * ProgressBar — 프로젝트 진행률 `42% · 5/12 완료` (DASH-01, UI-DESIGN §3.2·S3).
 * 숫자는 서버가 계산한 Project.progress를 그대로 쓴다(반올림을 서버와 다르게 하지 않기 위해).
 * 모양은 시안(김서현 확인): 막대 6px·끝 둥글게, 빈 부분 neutral-100, 채운 부분 primary, 글자 12px.
 *
 * @param {object} props
 * @param {{ total: number, done: number, percent: number }} props.progress
 * @param {string} [props.barClassName] 막대 길이. 칸반 머리말 `w-[260px]`, 목록 카드는 기본값(남은 폭)
 * @param {string} [props.className]
 */
export default function ProgressBar({
  progress,
  barClassName = "flex-1",
  className,
}) {
  const { total, done, percent } = progress;
  // 서버 값이 어긋나도 막대가 칸을 넘지 않게
  const width = Math.min(Math.max(percent, 0), 100);

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div
        role="progressbar"
        aria-label="프로젝트 진행률"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={width}
        className={cn(
          "h-1.5 overflow-hidden rounded-full bg-neutral-100",
          barClassName,
        )}
      >
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${width}%` }}
        />
      </div>
      <p className="shrink-0 text-xs text-neutral-500">
        <span className="font-bold text-neutral-900">{percent}%</span> · {done}/
        {total} 완료
      </p>
    </div>
  );
}
