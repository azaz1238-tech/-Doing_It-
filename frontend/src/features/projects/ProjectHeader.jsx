import { Link } from "react-router";
import Avatar from "../../core/ui/Avatar";
import Skeleton from "../../core/ui/Skeleton";
import { cn } from "../../core/utils/cn";
import { formatPeriod } from "../../core/utils/date";
import ProgressBar from "./ProgressBar";

// 아바타 묶음에 보여 줄 최대 인원. 넘치면 +n (UI-DESIGN §3.2)
const MAX_AVATARS = 4;

/**
 * ProjectHeader — UI-DESIGN §3.2 (S4 칸반 보드, S7 설정 위쪽). PRJ-07.
 * 데이터는 받아서 그리기만 한다. API는 부르는 화면(S4·S7)이 한 번 불러 넘긴다(COMPONENTS §1).
 *
 * @param {object} props
 * @param {object | null} props.project Project 응답. 없으면 스켈레톤
 * @param {Array<{ user_id: number, name: string }> | null} [props.members]
 *   Member 목록(OWNER 먼저). 없으면 아바타 묶음을 그리지 않는다
 * @param {"board" | "settings"} props.active 선택된 탭
 * @param {import("react").ReactNode} [props.actions] 오른쪽 버튼 자리 (S4: `+ 업무 추가`)
 */
export default function ProjectHeader({ project, members, active, actions }) {
  return (
    <header className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        {project ? (
          <div className="min-w-0">
            <Link
              to="/projects"
              className="text-xs text-neutral-500 hover:text-neutral-700"
            >
              프로젝트 ›
            </Link>
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-2">
              <h1 className="text-2xl font-bold break-all text-neutral-900">
                {project.name}
              </h1>
              <p className="text-sm text-neutral-500">
                {/* 시작일·종료일은 선택 항목이라 없을 수 있다. S3 카드와 같게 "기간 없음" */}
                {formatPeriod(project.start_date, project.end_date) ||
                  "기간 없음"}
              </p>
              {members?.length > 0 && (
                <MemberStack projectId={project.id} members={members} />
              )}
              {/* 진행률 (DASH-01). 응답에 progress가 없으면(이전 API) 그리지 않는다 */}
              {project.progress && (
                <ProgressBar
                  progress={project.progress}
                  barClassName="w-[260px]"
                />
              )}
            </div>
          </div>
        ) : (
          <div aria-hidden="true" className="flex flex-col gap-2">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-7 w-48" />
          </div>
        )}
        {actions}
      </div>

      {/* P0 탭은 보드·설정 2개. 설정 탭은 모든 멤버에게 보인다(UI-DESIGN §3.2, S7) */}
      <nav
        aria-label="프로젝트 메뉴"
        className="flex gap-1 border-b border-neutral-200"
      >
        <Tab
          to={project ? `/projects/${project.id}` : null}
          selected={active === "board"}
        >
          보드
        </Tab>
        <Tab
          to={project ? `/projects/${project.id}/settings` : null}
          selected={active === "settings"}
        >
          설정
        </Tab>
      </nav>
    </header>
  );
}

// 멤버 아바타 최대 4개 + `+n`. 누르면 S7(설정)로 간다.
function MemberStack({ projectId, members }) {
  const shown = members.slice(0, MAX_AVATARS);
  const rest = members.length - shown.length;

  return (
    <Link
      to={`/projects/${projectId}/settings`}
      aria-label={`멤버 ${members.length}명, 설정에서 보기`}
      className="flex items-center -space-x-1 rounded-full"
    >
      {shown.map((m) => (
        <Avatar
          key={m.user_id}
          // Avatar는 { id, name }을 받는다. Member 응답은 user_id라서 바꿔 넘긴다.
          user={{ id: m.user_id, name: m.name }}
          size="sm"
          className="ring-2 ring-white"
        />
      ))}
      {rest > 0 && (
        <span className="inline-flex size-6 items-center justify-center rounded-full bg-neutral-200 text-xs font-semibold text-neutral-600 ring-2 ring-white">
          +{rest}
        </span>
      )}
    </Link>
  );
}

// 탭 하나. 선택 여부는 부모가 active로 정한다.
// (NavLink 자동 판단을 쓰면 S6 주소 /projects/:id/tasks/:taskId 에서 보드 탭이 꺼진다)
function Tab({ to, selected, children }) {
  const className = cn(
    "-mb-px border-b-2 px-3 py-2 text-sm font-semibold",
    selected
      ? "border-primary text-primary"
      : "border-transparent text-neutral-500 hover:text-neutral-700",
  );

  // 프로젝트를 불러오기 전에는 주소를 모르므로 글자만 보여 준다.
  if (!to) return <span className={className}>{children}</span>;

  return (
    <Link
      to={to}
      aria-current={selected ? "page" : undefined}
      className={className}
    >
      {children}
    </Link>
  );
}
