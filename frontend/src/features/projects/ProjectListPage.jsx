import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router";
import Button from "../../core/ui/Button";
import EmptyState from "../../core/ui/EmptyState";
import { CalendarIcon, FolderIcon, PlusIcon } from "../../core/ui/icons";
import { SkeletonList } from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import { formatPeriod } from "../../core/utils/date";
import { listProjects } from "./api";
import { ROLE_STYLES } from "./projectRules";
import CreateProjectModal from "./CreateProjectModal";

// S3 프로젝트 목록 — PRJ-01, PRJ-02 · US-05, 06 · UI-DESIGN S3 (모양은 시안 v0.3, 문구는 명세)
const GRID = "grid gap-4 sm:grid-cols-2 lg:grid-cols-3"; // 데스크톱 3열 → 태블릿 2열 → 모바일 1열

export default function ProjectListPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [data, setData] = useState(null); // null = 불러오는 중
  const [loadFailed, setLoadFailed] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  // 처음 그릴 때 data=null(불러오는 중)이라 effect 안에서는 상태를 바로 바꾸지 않고 응답만 기다린다.
  const fetchProjects = useCallback(
    () =>
      listProjects()
        .then(setData)
        .catch((error) => {
          setLoadFailed(true);
          toast.error(
            error.response?.data?.message ?? "잠시 후 다시 시도해 주세요",
          );
        }),
    [toast],
  );

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // "다시 시도": 불러오는 중 상태로 되돌린 뒤 다시 요청
  const retry = () => {
    setLoadFailed(false);
    setData(null);
    fetchProjects();
  };

  const openCreate = () => setCreateOpen(true);
  const isEmpty = data?.items.length === 0;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 whitespace-nowrap text-2xl font-bold text-neutral-900">
          내 프로젝트
          {data && (
            <span className="rounded-md bg-neutral-100 px-2 py-0.5 text-sm font-semibold text-neutral-600">
              {data.total}
            </span>
          )}
        </h1>
        {/* 빈 상태에서는 EmptyState 버튼 하나만 보인다 */}
        {data && !isEmpty && (
          <Button onClick={openCreate}>
            <PlusIcon />새 프로젝트
          </Button>
        )}
      </header>

      {loadFailed ? (
        <div className="flex flex-col items-center gap-3 py-16 text-neutral-500">
          <p>프로젝트 목록을 불러오지 못했습니다</p>
          <Button variant="secondary" onClick={retry}>
            다시 시도
          </Button>
        </div>
      ) : data === null ? (
        <SkeletonList count={3} className={GRID} />
      ) : isEmpty ? (
        // PRJ-02-b
        <EmptyState
          icon={FolderIcon}
          title="프로젝트가 없습니다"
          description="프로젝트를 만들어 보세요"
          action={
            <Button onClick={openCreate}>
              <PlusIcon />첫 프로젝트 만들기
            </Button>
          }
        />
      ) : (
        <ul className={GRID}>
          {data.items.map((project) => (
            <li key={project.id}>
              <ProjectCard project={project} />
            </li>
          ))}
        </ul>
      )}

      {createOpen && (
        <CreateProjectModal
          onClose={() => setCreateOpen(false)}
          // 만들기 성공 → 새 프로젝트의 S4 (UI-DESIGN S3)
          onCreated={(project) => navigate(`/projects/${project.id}`)}
        />
      )}
    </div>
  );
}

// 카드: 이름·기간·내 역할 (PRJ-02-a). 누르면 칸반(S4)
function ProjectCard({ project }) {
  const period = formatPeriod(project.start_date, project.end_date);
  return (
    <Link
      to={`/projects/${project.id}`}
      className="flex h-full flex-col gap-3 rounded-xl border border-neutral-200 bg-white p-5 transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-primary"
    >
      <div className="flex items-center gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
          <FolderIcon />
        </span>
        <h2 className="min-w-0 flex-1 truncate text-[15px] font-bold text-neutral-900">
          {project.name}
        </h2>
        <span
          className={cn(
            "rounded px-2 py-0.5 text-xs font-semibold",
            ROLE_STYLES[project.my_role],
          )}
        >
          {project.my_role}
        </span>
      </div>
      <p className="flex items-center gap-1.5 text-sm text-neutral-500">
        <CalendarIcon />
        {period || "기간 없음"}
      </p>
      {/* P1 진행률(DASH-01) 자리 — P0에서는 비워 둔다. 나중에 막대를 넣어도 카드 높이가 바뀌지 않게 */}
      <div className="h-8" aria-hidden="true" />
    </Link>
  );
}
