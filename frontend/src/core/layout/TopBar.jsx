import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useNavigate } from "react-router";
import { useAuth } from "../auth/useAuth";
import Avatar from "../ui/Avatar";
import { ChevronDownIcon, LogOutIcon } from "../ui/icons";
import { cn } from "../utils/cn";

/**
 * TopBar — UI-DESIGN §3.1 (S3~S8)
 * 왼쪽: 로고 `동잇` → /projects · 메뉴: `프로젝트` · 오른쪽: 아바타 + 이름 ▾ → `로그아웃`
 * P1에서 `내 대시보드` 메뉴, `내 정보 수정`(AUTH-06) 메뉴가 추가된다.
 */
export default function TopBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // 메뉴 바깥 클릭·ESC로 닫기
  useEffect(() => {
    if (!menuOpen) return;
    const handlePointerDown = (event) => {
      if (!menuRef.current?.contains(event.target)) setMenuOpen(false);
    };
    const handleKeyDown = (event) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <header className="sticky top-0 z-30 border-b border-neutral-200 bg-white">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-8 px-4 sm:px-6">
        {/* 로고: 시안 v0.3 — "동"은 본문색, "잇"은 주 색 */}
        <Link to="/projects" className="text-lg font-bold text-neutral-900">
          동<span className="text-primary">잇</span>
        </Link>

        {/* 현재 메뉴: 시안 v0.3 — 굵은 본문색 글자 + 아래 밑줄 (헤더 아래 테두리에 붙는다) */}
        <nav aria-label="주 메뉴" className="flex items-stretch self-stretch">
          <NavLink
            to="/projects"
            className={({ isActive }) =>
              cn(
                "-mb-px flex items-center border-b-2 px-1 font-semibold",
                isActive
                  ? "border-neutral-900 text-neutral-900"
                  : "border-transparent text-neutral-500 hover:text-neutral-900",
              )
            }
          >
            프로젝트
          </NavLink>
        </nav>

        {user && (
          <div ref={menuRef} className="relative ml-auto">
            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-neutral-100"
            >
              <Avatar user={user} size="sm" />
              <span className="max-w-32 truncate font-medium">{user.name}</span>
              <ChevronDownIcon className="text-neutral-500" />
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 mt-1 w-40 rounded-lg border border-neutral-200 bg-white py-1 shadow-lg"
              >
                <button
                  type="button"
                  role="menuitem"
                  onClick={handleLogout}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-neutral-100"
                >
                  <LogOutIcon className="text-neutral-500" />
                  로그아웃
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
