import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import ErrorPage from "../../core/ui/ErrorPage";
import Skeleton from "../../core/ui/Skeleton";
import { ClockIcon } from "../../core/ui/icons";
import EmptyState from "../../core/ui/EmptyState";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import { formatDateTime } from "../../core/utils/date";
import { activityTaskTitle, describeActivity } from "../tasks/activityText";
import { getProject, listMembers, listProjectActivities } from "./api";
import ProgressBar from "./ProgressBar";
import ProjectHeader from "./ProjectHeader";

// 프로젝트 통계 (P1) — REQUIREMENTS §6 `/projects/:id/stats`, UI-DESIGN §3.2(탭은 보드와 설정 사이)
// 범위: 진행률(DASH-01) · 담당자별 현황(DASH-02) · 마감 임박·지연(DASH-03) · 최근 활동 20건(LOG-03)
// 지금은 진행률 · 최근 활동(T-F4-07). 임박·지연(T-F5-06)·담당자별(T-F5-10)은 API가 나오면 구역을 더한다.

const RECENT_SIZE = 20; // LOG-03-b

// 페이지 진입 오류 → S8 안내 화면 (설정 화면과 같은 기준). LOG-03-c: 비멤버는 안내만 본다.
function pageErrorOf(error) {
  const code = error.response?.data?.code;
  if (code === "NOT_PROJECT_MEMBER") return "403";
  if (code === "PROJECT_NOT_FOUND") return "404";
  return null;
}

// 프로젝트가 바뀌면 상태를 모두 새로 시작하도록 id를 key로 준다(BoardPage·설정과 같음).
export default function ProjectStatsPage() {
  const { id } = useParams();
  return <Stats key={id} projectId={id} />;
}

function Stats({ projectId }) {
  const toast = useToast();
  const [project, setProject] = useState(null);
  const [members, setMembers] = useState(null);
  const [pageError, setPageError] = useState(null); // "403" | "404" | null

  useEffect(() => {
    let ignore = false;
    getProject(projectId)
      .then((data) => !ignore && setProject(data))
      .catch((error) => {
        if (ignore) return;
        const kind = pageErrorOf(error);
        if (kind) setPageError(kind);
        else
          toast.error(
            error.response?.data?.message ?? "프로젝트를 불러오지 못했습니다",
          );
      });
    // 헤더 아바타용. 실패하면 아바타만 그리지 않는다(권한·없음 안내는 getProject 쪽이 맡는다).
    listMembers(projectId)
      .then((data) => !ignore && setMembers(data.items))
      .catch(() => !ignore && setMembers([]));
    return () => {
      ignore = true;
    };
  }, [projectId, toast]);

  if (pageError === "403") return <ErrorPage type="403" />;
  if (pageError === "404")
    return <ErrorPage type="404" title="프로젝트를 찾을 수 없습니다" />;

  return (
    <div className="flex flex-col gap-6">
      <ProjectHeader project={project} members={members} active="stats" />

      {project ? (
        <div className="flex flex-col gap-6">
          {/* 진행률 (DASH-01). 응답에 progress가 없으면(이전 API) 구역을 그리지 않는다 */}
          {project.progress && (
            <Section title="진행률">
              <ProgressBar progress={project.progress} />
            </Section>
          )}
          <RecentActivities projectId={project.id} onPageError={setPageError} />
        </div>
      ) : (
        <div aria-hidden="true" className="flex flex-col gap-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}
    </div>
  );
}

function Section({ title, className, children }) {
  return (
    <section
      className={cn(
        "rounded-xl border border-neutral-200 bg-white p-6",
        className,
      )}
    >
      {/* TODO(Figma): 통계 구역 제목·배치는 시안 확정 전 추정값 */}
      <h2 className="mb-4 text-lg font-bold text-neutral-900">{title}</h2>
      {children}
    </section>
  );
}

// 최근 활동 20건 (LOG-03-b). 최신순, 누르면 업무 상세(S6). 삭제된 업무는 누를 수 없다.
function RecentActivities({ projectId, onPageError }) {
  const toast = useToast();
  const [items, setItems] = useState(null); // null = 불러오는 중
  const [loadFailed, setLoadFailed] = useState(false);

  // 처음 그릴 때 items=null(불러오는 중)이라 effect 안에서는 응답만 기다린다(S3 목록과 같은 방식).
  const fetchActivities = useCallback(
    () =>
      listProjectActivities(projectId, { size: RECENT_SIZE })
        .then((data) => setItems(data.items))
        .catch((error) => {
          const kind = pageErrorOf(error);
          if (kind) {
            onPageError(kind); // 보는 사이 멤버에서 빠졌거나 프로젝트가 지워진 경우
            return;
          }
          setLoadFailed(true);
          toast.error(
            error.response?.data?.message ?? "잠시 후 다시 시도해 주세요",
          );
        }),
    [projectId, onPageError, toast],
  );

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  const retry = () => {
    setLoadFailed(false);
    setItems(null);
    fetchActivities();
  };

  return (
    <Section title="최근 활동">
      {loadFailed ? (
        <div className="flex flex-col items-center gap-3 py-8 text-sm text-neutral-500">
          <p>최근 활동을 불러오지 못했습니다</p>
          <Button variant="secondary" onClick={retry}>
            다시 시도
          </Button>
        </div>
      ) : items === null ? (
        <div role="status" aria-live="polite" className="flex flex-col gap-3">
          <span className="sr-only">불러오는 중입니다</span>
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        // TODO(Figma): 최근 활동 빈 상태 문구는 시안 확정 전 추정값
        <EmptyState
          variant="column"
          title="아직 활동이 없습니다"
          description="업무를 만들거나 바꾸면 여기에 보입니다"
        />
      ) : (
        <ul className="divide-y divide-neutral-200">
          {items.map((activity) => (
            <li key={activity.id}>
              <ActivityRow projectId={projectId} activity={activity} />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

// 한 줄: (아바타) 이름 · 업무 제목 / 바뀐 내용 · 시각
// 이름·제목은 JSX 글자로만 넣는다(dangerouslySetInnerHTML 금지).
function ActivityRow({ projectId, activity }) {
  const title = activityTaskTitle(activity);
  const deleted = activity.task_id == null;

  const body = (
    <>
      <Avatar user={activity.user} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-neutral-900">
          <span className="font-semibold">{activity.user.name}</span>
          <span className="text-neutral-400"> · </span>
          <span className={deleted ? "text-neutral-400" : undefined}>
            {title}
          </span>
        </p>
        <p className="truncate text-xs text-neutral-500">
          {describeActivity(activity)}
        </p>
      </div>
      <time
        dateTime={activity.created_at}
        className="flex shrink-0 items-center gap-1 text-xs text-neutral-400"
      >
        <ClockIcon />
        {formatDateTime(activity.created_at)}
      </time>
    </>
  );

  const rowClass = "flex items-center gap-3 py-3";
  // 삭제된 업무는 상세가 없으므로 링크로 만들지 않는다(LOG-03-b)
  if (deleted) return <div className={rowClass}>{body}</div>;

  return (
    <Link
      to={`/projects/${projectId}/tasks/${activity.task_id}`}
      className={cn(
        rowClass,
        "-mx-2 rounded-lg px-2 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-primary",
      )}
    >
      {body}
    </Link>
  );
}
