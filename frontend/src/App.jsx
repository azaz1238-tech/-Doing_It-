import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router";
import ProtectedRoute from "./core/auth/ProtectedRoute";
import AppLayout from "./core/layout/AppLayout";
import ErrorPage from "./core/ui/ErrorPage";
import LoginPage from "./features/auth/LoginPage";
import SignupPage from "./features/auth/SignupPage";
import ProjectListPage from "./features/projects/ProjectListPage";
import BoardPage from "./features/tasks/BoardPage";
import TaskDetailModal from "./features/tasks/TaskDetailModal";

// 개발 서버에서만 쓰는 공통 컴포넌트 미리보기. 배포 빌드에서는 경로와 코드가 모두 빠진다.
const ComponentPreviewPage = import.meta.env.DEV
  ? lazy(() => import("./features/dev/ComponentPreviewPage"))
  : null;

// 임시 화면. 각 담당자가 실제 페이지를 만들면 import로 교체한다.
function Placeholder({ title }) {
  return <h1 className="p-6 text-xl font-bold">{title}</h1>;
}

// 화면 주소는 ARCHITECTURE §5.2를 따른다.
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      {/* 개발용: 로그인 없이 TopBar + 공통 컴포넌트를 본다 */}
      {ComponentPreviewPage && (
        <Route element={<AppLayout />}>
          <Route
            path="/dev/components"
            element={
              <Suspense fallback={null}>
                <ComponentPreviewPage />
              </Suspense>
            }
          />
        </Route>
      )}
      {/* 로그인 후 화면은 TopBar가 있는 AppLayout 안에 그린다(UI-DESIGN §3.1). */}
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/projects" replace />} />
        <Route path="/projects" element={<ProjectListPage />} />
        <Route path="/projects/:id" element={<BoardPage />}>
          <Route path="tasks/:taskId" element={<TaskDetailModal />} />
        </Route>
        <Route
          path="/projects/:id/settings"
          element={<Placeholder title="설정" />}
        />
        <Route path="*" element={<ErrorPage type="404" />} />
      </Route>
    </Routes>
  );
}
