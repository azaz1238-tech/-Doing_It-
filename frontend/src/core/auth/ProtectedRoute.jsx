import { Navigate, useLocation } from "react-router";
import Button from "../ui/Button";
import { useAuth } from "./useAuth";

// 비로그인 사용자를 /login으로 보낸다. 화면 접근 편의용이며, 실제 권한 차단은 백엔드가 한다.
export default function ProtectedRoute({ children }) {
  const { user, loading, restoreFailed, retryRestore } = useAuth();
  const location = useLocation();

  // 로그인 상태 복원 중에는 아무것도 그리지 않는다. Skeleton(FE-03)이 생기면 교체한다.
  if (loading) return null;

  // 토큰은 있는데 서버에 닿지 못해 복원하지 못함 → 로그인 화면 대신 다시 시도(D9-04)
  if (restoreFailed) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 text-center text-neutral-500">
        {/* TODO(Figma): 서버 연결 실패 문구는 시안 확정 전 추정값 */}
        <p className="text-base font-semibold text-neutral-900">
          서버에 연결하지 못했습니다
        </p>
        <p className="text-sm">잠시 후 다시 시도해 주세요</p>
        <Button variant="secondary" onClick={retryRestore}>
          다시 시도
        </Button>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return children;
}
