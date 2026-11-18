import { Link } from "react-router";
import { CompassIcon, ShieldIcon } from "./icons";

// 문구는 UI-DESIGN S8 표(v1.6, 시안 Figma와 같음)를 따른다. 403 제목은 SPEC PRJ-07-a 따옴표 문구.
const DEFAULTS = {
  403: {
    icon: ShieldIcon,
    title: "접근 권한이 없습니다",
    description: "프로젝트 OWNER에게 멤버 추가를 요청해 주세요",
  },
  404: {
    icon: CompassIcon,
    title: "페이지를 찾을 수 없습니다",
    description: "주소가 바뀌었거나 삭제된 항목입니다",
  },
};

/**
 * ErrorPage — UI-DESIGN S8 (403·404 안내), NFR-09.
 * 컴포넌트 1개에 문구만 바꿔 쓴다. TopBar는 AppLayout이 그대로 그리고, 이 컴포넌트는 본문만 채운다.
 * 아이콘 · 제목 위 작은 숫자(`403`/`404`) · 제목 · 설명 · `프로젝트 목록으로` (시안 S8).
 * 403 NOT_PROJECT_MEMBER(페이지 진입)에만 쓴다. 버튼 동작의 403 FORBIDDEN은 토스트로 보여 준다.
 * 비멤버에게는 프로젝트 이름 같은 정보를 넣지 않는다(PRJ-07-a).
 *
 * @param {"403"|"404"} type
 * @param {string} [title] 기본 문구 대신 (예: 칸반 404 → "프로젝트를 찾을 수 없습니다")
 * @param {string} [description]
 */
export default function ErrorPage({ type = "404", title, description }) {
  const base = DEFAULTS[type] ?? DEFAULTS[404];
  const Icon = base.icon;
  return (
    // 모양은 EmptyState(page)와 같고, 제목 위 숫자만 더한다. 아이콘 상자는 시안 S8대로 회색(EmptyState는 파랑).
    <div className="flex flex-col items-center px-4 py-16 text-center">
      <div className="mb-5 flex size-16 items-center justify-center rounded-xl bg-neutral-100 text-neutral-500">
        <Icon size={28} />
      </div>
      <p className="mb-1 text-xs font-semibold tracking-widest text-neutral-400">
        {type}
      </p>
      <h2 className="text-base font-bold text-neutral-900">
        {title ?? base.title}
      </h2>
      <p className="mt-1.5 text-neutral-500">
        {description ?? base.description}
      </p>
      <Link
        to="/projects"
        className="mt-5 inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-white shadow-sm hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        프로젝트 목록으로
      </Link>
    </div>
  );
}
