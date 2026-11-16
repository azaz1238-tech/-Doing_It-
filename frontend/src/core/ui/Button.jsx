import { cn } from "../utils/cn";
import { LoaderIcon } from "./icons";

// Button — UI-DESIGN §5: Primary · Secondary · Ghost · Danger
const VARIANTS = {
  primary: "bg-primary text-white shadow-sm hover:bg-primary-hover",
  secondary:
    "border border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50",
  ghost: "text-neutral-600 hover:bg-neutral-100",
  danger: "bg-danger text-white hover:bg-danger/90",
};

const SIZES = {
  sm: "h-8 px-3 text-xs",
  md: "h-9 px-4 text-sm",
};

/**
 * @param {"primary"|"secondary"|"ghost"|"danger"} variant
 * @param {"sm"|"md"} size
 * @param {boolean} loading 요청 중이면 true — 버튼이 비활성화되어 두 번 제출을 막는다.
 */
export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  type = "button",
  className,
  children,
  ...rest
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium whitespace-nowrap transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {loading && <LoaderIcon size={14} />}
      {children}
    </button>
  );
}
