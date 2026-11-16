import { useCallback, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { cn } from "../utils/cn";
import { XIcon } from "./icons";

const DIRTY_MESSAGE = "작성 중인 내용이 사라집니다. 닫으시겠습니까?";

const SIZES = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

/**
 * Modal — UI-DESIGN §5: ESC·바깥 클릭으로 닫기 (입력 중이면 확인)
 * 사용처: S3 생성 모달, S5 업무 등록, S6 업무 상세, S7 삭제 확인
 *
 * @param {boolean} open
 * @param {() => void} onClose
 * @param {string} title
 * @param {React.ReactNode} [footer] 아래쪽 버튼 영역
 * @param {boolean} [isDirty] 입력 중이면 true — 닫기 전에 확인을 묻는다.
 */
export default function Modal({
  open,
  onClose,
  title,
  footer,
  isDirty = false,
  size = "md",
  children,
}) {
  const dialogRef = useRef(null);
  const titleId = useId();

  const requestClose = useCallback(() => {
    // TODO: 브라우저 기본 확인창 대신 ConfirmDialog로 바꿀지 Figma와 맞춰 본다.
    if (isDirty && !window.confirm(DIRTY_MESSAGE)) return;
    onClose();
  }, [isDirty, onClose]);

  // 열릴 때 포커스를 모달로 옮기고 배경 스크롤을 막는다. 닫히면 원래 자리로 포커스를 돌려준다.
  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialogRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus?.();
    };
  }, [open]);

  // ESC로 닫기. 모달 위에 모달(ConfirmDialog)이 뜨면 포커스가 있는 맨 위 모달만 닫는다.
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event) => {
      if (event.key !== "Escape") return;
      if (!dialogRef.current?.contains(document.activeElement)) return;
      event.stopPropagation();
      requestClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, requestClose]);

  if (!open) return null;

  return createPortal(
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4"
      // 바깥(어두운 배경)을 눌렀을 때만 닫는다. 모달 안에서 드래그하다 바깥에서 놓는 경우는 제외.
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) requestClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn(
          "flex max-h-[90vh] w-full flex-col rounded-xl bg-white shadow-xl outline-none",
          SIZES[size],
        )}
      >
        <header className="flex items-center justify-between gap-4 border-b border-neutral-200 px-5 py-4">
          <h2 id={titleId} className="text-base font-semibold">
            {title}
          </h2>
          <button
            type="button"
            onClick={requestClose}
            aria-label="닫기"
            className="rounded-md p-1 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
          >
            <XIcon size={18} />
          </button>
        </header>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && (
          <footer className="flex justify-end gap-2 border-t border-neutral-200 px-5 py-3">
            {footer}
          </footer>
        )}
      </div>
    </div>,
    document.body,
  );
}
