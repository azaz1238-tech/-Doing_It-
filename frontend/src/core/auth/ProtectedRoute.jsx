import { Navigate, useLocation } from "react-router";
import { useAuth } from "./useAuth";

// 비로그인 사용자를 /login으로 보낸다. 화면 접근 편의용이며, 실제 권한 차단은 백엔드가 한다.
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  // 로그인 상태 복원 중에는 아무것도 그리지 않는다. Skeleton(FE-03)이 생기면 교체한다.
  if (loading) return null;

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
