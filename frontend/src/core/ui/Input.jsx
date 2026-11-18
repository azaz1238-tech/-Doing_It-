import { useId, useState } from "react";
import { cn } from "../utils/cn";
import { countChars } from "../utils/text";
import { CheckIcon, EyeIcon, EyeOffIcon } from "./icons";

/**
 * Input — 라벨 + 입력창 + 도움말/오류/성공 문구 (동잇 UI 시안 v0.3)
 * React 19는 ref를 일반 prop으로 넘길 수 있어 forwardRef가 필요 없다.
 *
 * @param {string} label 화면에 보이는 라벨
 * @param {string} [labelHint] 라벨 옆 흐린 안내 (시안 S2: "아이디 · 영문 소문자·숫자 4~20자")
 * @param {string} [error] 오류 문구. 있으면 빨간 테두리와 함께 표시하고 aria-invalid를 켠다.
 * @param {string} [success] 성공 문구 (예: "✓ 사용할 수 있습니다"). error가 있으면 보이지 않는다.
 * @param {string} [hint] 오류·성공 문구가 없을 때 보이는 도움말
 * @param {number} [maxCount] 글자 수 표시 (시안 S3·S5·S7: "6/30"). 넘으면 빨간색.
 *   서버와 같게 앞뒤 공백을 빼고, 이모지도 1자로 센다.
 *   입력을 막지 않고 보여 주기만 한다 — 막으려면 maxLength를 따로 넘긴다.
 * type="password"면 오른쪽에 보기·숨기기 버튼이 붙는다.
 */
export default function Input({
  label,
  labelHint,
  error,
  success,
  hint,
  maxCount,
  id,
  type = "text",
  required,
  className,
  ...rest
}) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const messageId = `${inputId}-message`;
  const [showPassword, setShowPassword] = useState(false);

  const isPassword = type === "password";
  // 서버 검증과 같게 앞뒤 공백을 빼고 코드 포인트로 센다(#49). maxCount를 쓰는 칸은 모두 서버가 trim하는 칸이다.
  const length = countChars(String(rest.value ?? "").trim());
  const overCount = maxCount != null && length > maxCount;
  const message = error || success || hint;
  const hasRightSlot = isPassword || maxCount != null;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && (
        <label htmlFor={inputId} className="font-semibold text-neutral-900">
          {label}
          {required && <span className="ml-0.5 text-danger">*</span>}
          {labelHint && (
            <span className="ml-1 text-xs font-normal text-neutral-400">
              · {labelHint}
            </span>
          )}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type={isPassword && showPassword ? "text" : type}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={message ? messageId : undefined}
          className={cn(
            "h-10 w-full rounded-lg border bg-white px-3 text-sm text-neutral-900 placeholder:text-neutral-400",
            "focus:outline-2 focus:-outline-offset-1",
            "disabled:cursor-not-allowed disabled:bg-neutral-100",
            hasRightSlot && "pr-14",
            error
              ? "border-danger focus:outline-danger"
              : "border-neutral-300 focus:outline-primary",
          )}
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((show) => !show)}
            aria-label={showPassword ? "비밀번호 숨기기" : "비밀번호 보기"}
            aria-pressed={showPassword}
            className="absolute inset-y-0 right-0 flex items-center px-3 text-neutral-400 hover:text-neutral-700"
          >
            {showPassword ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        )}
        {!isPassword && maxCount != null && (
          <span
            className={cn(
              "pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs",
              overCount ? "font-semibold text-danger" : "text-neutral-400",
            )}
          >
            {length}/{maxCount}
          </span>
        )}
      </div>
      {message && (
        <p
          id={messageId}
          className={cn(
            "flex items-center gap-1 text-xs",
            error
              ? "text-danger"
              : success
                ? "text-success"
                : "text-neutral-500",
          )}
        >
          {!error && success && <CheckIcon size={14} />}
          {message}
        </p>
      )}
    </div>
  );
}
