import { createContext, useContext } from "react";

// 컴포넌트(ToastProvider.jsx)와 훅을 분리한다 — useAuth.js와 같은 이유(react-refresh 린트 규칙).
export const ToastContext = createContext(null);

/**
 * 사용 예:
 *   const toast = useToast();
 *   toast.success("프로젝트를 만들었습니다");
 *   toast.error(err.response?.data?.message ?? "잠시 후 다시 시도해 주세요");
 *   toast.warning("로그인이 만료되었습니다. 다시 로그인해 주세요");  // 세션 만료
 */
export function useToast() {
  const value = useContext(ToastContext);
  if (!value) {
    throw new Error("useToast는 ToastProvider 안에서만 사용할 수 있습니다.");
  }
  return value;
}
