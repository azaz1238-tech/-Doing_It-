import { Outlet } from "react-router";
import TopBar from "./TopBar";

// 로그인 후 화면(S3~S8)의 공통 틀. 로그인·회원가입(S1·S2)에는 쓰지 않는다.
export default function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
