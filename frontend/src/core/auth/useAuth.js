import { createContext, useContext } from "react";

// 컴포넌트 파일(AuthContext.jsx)과 분리해 둔다. 한 파일에서 컴포넌트와 훅을 함께 내보내면
// Vite 빠른 새로고침이 동작하지 않는다(react-refresh 린트 규칙).
export const AuthContext = createContext(null);

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth는 AuthProvider 안에서만 사용할 수 있습니다.");
  }
  return value;
}
