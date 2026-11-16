import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "../utils/cn";
import { CheckIcon, LogOutIcon, TriangleAlertIcon } from "./icons";
import { ToastContext } from "./useToast";

// Toast — UI-DESIGN §5: 성공 · 오류 · 세션 만료. 화면 아래 가운데, 3초 후 사라짐 (되돌리기 없음, §8-7)
// 색·아이콘은 동잇 UI 시안 v0.3 "빈 화면·로딩·알림·확인 창"을 따른다.
const DURATION_MS = 3000;

const STYLES = {
  success: {
    className: "bg-neutral-900 text-white",
    Icon: CheckIcon,
    iconClass: "text-success-soft",
  },
  error: {
    className: "bg-danger-strong text-white",
    Icon: TriangleAlertIcon,
    iconClass: "text-white",
  },
  // 세션 만료 안내
  warning: {
    className: "bg-neutral-600 text-white",
    Icon: LogOutIcon,
    iconClass: "text-white",
  },
};

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);
  const timers = useRef(new Map());

  const remove = useCallback((id) => {
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    setToasts((list) => list.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    (type, message) => {
      const id = ++nextId.current;
      setToasts((list) => [...list, { id, type, message }]);
      timers.current.set(
        id,
        setTimeout(() => remove(id), DURATION_MS),
      );
    },
    [remove],
  );

  // 화면이 사라질 때 남은 타이머를 정리한다.
  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((timer) => clearTimeout(timer));
  }, []);

  const toast = useMemo(
    () => ({
      success: (message) => show("success", message),
      error: (message) => show("error", message),
      warning: (message) => show("warning", message),
    }),
    [show],
  );

  return (
    <ToastContext.Provider value={toast}>
      {children}
      {createPortal(
        <div
          // 화면 읽기 프로그램이 새 알림을 읽어 준다.
          role="status"
          aria-live="polite"
          className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex flex-col items-center gap-2 px-4"
        >
          {toasts.map(({ id, type, message }) => {
            const { className, Icon, iconClass } = STYLES[type];
            return (
              <div
                key={id}
                className={cn(
                  "pointer-events-auto flex max-w-md items-center gap-2 rounded-lg px-4 py-3 shadow-lg",
                  className,
                )}
              >
                <Icon size={18} className={iconClass} />
                {/* 서버 message도 텍스트로만 넣는다(dangerouslySetInnerHTML 금지). */}
                <span>{message}</span>
              </div>
            );
          })}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  );
}
