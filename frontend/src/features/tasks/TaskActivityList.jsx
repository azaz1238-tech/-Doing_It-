import { useCallback, useEffect, useState } from "react";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import Skeleton from "../../core/ui/Skeleton";
import { formatDateTime } from "../../core/utils/date";
import { describeActivity } from "./activityText";
import { listTaskActivities } from "./api";

/**
 * 업무 상세의 변경 이력 목록 — LOG-03-a, UI-DESIGN S6 (T-F4-06)
 * 한 줄: (아바타) 이름 · 바뀐 내용 · 시각. 예: "민호 · 마감일 11/20 → 11/25 · 방금 전". 최신순(서버 순서).
 *
 * @param {number} taskId
 * @param {number} version 상세에서 속성을 저장할 때마다 바뀌는 값 → 이력을 다시 불러와 맨 위에 보인다
 * @param {(total: number) => void} [onTotal] 탭 제목의 개수(`변경 이력 n`)용
 */
export default function TaskActivityList({ taskId, version, onTotal }) {
  const [items, setItems] = useState(null); // null = 불러오는 중
  const [loadFailed, setLoadFailed] = useState(false);

  // 다시 불러올 때는 지금 목록을 둔 채 바꾼다(저장할 때마다 스켈레톤이 깜빡이지 않게).
  // 403·404는 모달이 업무를 불러올 때 처리하므로 여기서는 실패 표시만 한다.
  const fetchActivities = useCallback(
    () =>
      listTaskActivities(taskId)
        .then((data) => {
          setItems(data.items);
          setLoadFailed(false);
          onTotal?.(data.total);
        })
        .catch(() => setLoadFailed(true)),
    [taskId, onTotal],
  );

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities, version]);

  const retry = () => {
    setLoadFailed(false);
    setItems(null);
    fetchActivities();
  };

  if (loadFailed && items === null) {
    return (
      <div className="flex flex-col items-center gap-3 py-6 text-sm text-neutral-500">
        <p>변경 이력을 불러오지 못했습니다</p>
        <Button variant="secondary" size="sm" onClick={retry}>
          다시 시도
        </Button>
      </div>
    );
  }

  if (items === null) {
    return (
      <div role="status" aria-live="polite" className="flex flex-col gap-2">
        <span className="sr-only">불러오는 중입니다</span>
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  }

  // 업무를 만들면 CREATED 1행이 생기므로 보통은 비지 않는다(P0 전 데이터 대비)
  if (items.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-neutral-500">
        변경 이력이 없습니다
      </p>
    );
  }

  return (
    <ul className="divide-y divide-neutral-100">
      {items.map((activity) => (
        <li key={activity.id} className="flex items-start gap-2.5 py-2.5">
          <Avatar user={activity.user} size="sm" />
          {/* 이름·내용은 JSX 글자로만 넣는다(dangerouslySetInnerHTML 금지) */}
          <p className="min-w-0 flex-1 text-sm break-words text-neutral-700">
            <span className="font-semibold text-neutral-900">
              {activity.user.name}
            </span>
            <span className="text-neutral-400"> · </span>
            {describeActivity(activity)}
          </p>
          <time
            dateTime={activity.created_at}
            className="shrink-0 pt-0.5 text-xs text-neutral-400"
          >
            {formatDateTime(activity.created_at)}
          </time>
        </li>
      ))}
    </ul>
  );
}
