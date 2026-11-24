import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router";
import ProtectedRoute from "./core/auth/ProtectedRoute";
import AppLayout from "./core/layout/AppLayout";
import ErrorPage from "./core/ui/ErrorPage";
import LoginPage from "./features/auth/LoginPage";
import SignupPage from "./features/auth/SignupPage";
import ProjectListPage from "./features/projects/ProjectListPage";
import ProjectSettingsPage from "./features/projects/ProjectSettingsPage";
import ProjectStatsPage from "./features/projects/ProjectStatsPage";
import BoardPage from "./features/tasks/BoardPage";
import GanttPage from "./features/tasks/GanttPage";
import MyDashboardPage from "./features/tasks/MyDashboardPage";
import TaskDetailModal from "./features/tasks/TaskDetailModal";

// 개발 서버에서만 쓰는 공통 컴포넌트 미리보기. 배포 빌드에서는 경로와 코드가 모두 빠진다.
const ComponentPreviewPage = import.meta.env.DEV
  ? lazy(() => import("./features/dev/ComponentPreviewPage"))
  : null;

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
        <Route path="/" element={<MyDashboardPage />} />
        <Route path="/projects" element={<ProjectListPage />} />
        <Route path="/projects/:id" element={<BoardPage />}>
          <Route path="tasks/:taskId" element={<TaskDetailModal />} />
        </Route>
        {/* 간트(P2, TASK-12) — 막대를 누르면 업무 상세(S6)가 간트 위에 열린다 */}
        <Route path="/projects/:id/gantt" element={<GanttPage />}>
          <Route path="tasks/:taskId" element={<TaskDetailModal />} />
        </Route>
        <Route path="/projects/:id/stats" element={<ProjectStatsPage />} />
        <Route
          path="/projects/:id/settings"
          element={<ProjectSettingsPage />}
        />
        <Route path="*" element={<ErrorPage type="404" />} />
      </Route>
    </Routes>
  );
}
