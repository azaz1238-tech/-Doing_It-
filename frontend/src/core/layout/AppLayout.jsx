import { Outlet } from "react-router";
import { useAuth } from "../auth/useAuth";
import TopBar from "./TopBar";

// 로그인 후 화면(S3~S8)의 공통 틀. 로그인·회원가입(S1·S2)에는 쓰지 않는다.
export default function AppLayout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-screen flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        {/* 내 이름을 바꾸면(AUTH-06) 지금 화면을 새로 그려 서버에서 다시 받는다.
            그래야 카드 담당자·댓글 작성자·멤버 목록이 새로고침 없이 새 이름으로 보인다(AUTH-06-a).
            필터·열린 업무는 주소에 있어 그대로 유지된다. */}
        <Outlet key={user?.name} />
      </main>
    </div>
  );
}
