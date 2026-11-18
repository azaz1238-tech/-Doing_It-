import { Link } from "react-router";
import EmptyState from "./EmptyState";
import { CompassIcon, ShieldAlertIcon } from "./icons";

// 기본 문구 — 403은 SPEC PRJ-07-a "접근 권한이 없습니다". 화면이 상황에 맞게 바꿔 쓴다.
const DEFAULTS = {
  403: {
    icon: ShieldAlertIcon,
    title: "접근 권한이 없습니다",
    description: "이 프로젝트의 멤버만 볼 수 있습니다",
  },
  404: {
    icon: CompassIcon,
    title: "페이지를 찾을 수 없습니다",
    description: "주소가 올바른지 확인해 주세요",
  },
};

/**
 * ErrorPage — UI-DESIGN S8 (403·404 안내), NFR-09.
 * 컴포넌트 1개에 문구만 바꿔 쓴다. TopBar는 AppLayout이 그대로 그리고, 이 컴포넌트는 본문만 채운다.
 * 403 NOT_PROJECT_MEMBER(페이지 진입)에만 쓴다. 버튼 동작의 403 FORBIDDEN은 토스트로 보여 준다.
 * 비멤버에게는 프로젝트 이름 같은 정보를 넣지 않는다(PRJ-07-a).
 *
 * @param {"403"|"404"} type
 * @param {string} [title] 기본 문구 대신 (예: "프로젝트를 찾을 수 없습니다")
 * @param {string} [description]
 */
export default function ErrorPage({ type = "404", title, description }) {
  const base = DEFAULTS[type] ?? DEFAULTS[404];
  return (
    <EmptyState
      icon={base.icon}
      title={title ?? base.title}
      description={description ?? base.description}
      action={
        <Link
          to="/projects"
          className="inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          프로젝트 목록으로
        </Link>
      }
    />
  );
}
