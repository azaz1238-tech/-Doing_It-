import { useEffect, useState } from "react";

import { useAuth } from "../../core/auth/useAuth";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import ConfirmDialog from "../../core/ui/ConfirmDialog";
import Skeleton from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import { formatDateTime } from "../../core/utils/date";
import {
  createComment,
  deleteComment,
  listComments,
  updateComment,
} from "./api";
import { charCount } from "./taskDisplay";

// 업무 상세 댓글 탭 (T-F4-04, CMT-01·02, UI-DESIGN S6·§9 #6, API-SPEC §6 댓글)
// - 목록은 오래된 순(서버 순서 그대로). 작성자·시각과 함께 보이고, 고친 댓글은 시각 옆에 "수정됨"
// - 입력칸에 글자 수 n/300. 비었거나 300자를 넘으면 등록하지 않는다(서버와 같게 앞뒤 공백을 빼고 셈)
// - 내 댓글에만 수정·삭제 버튼. 버튼 숨김은 편의일 뿐이고 권한은 서버가 막는다(남의 댓글 403)
// - 탭 제목의 숫자는 onCountChange(total)로 부모(탭 틀)에 알린다
// - 내용은 텍스트로만 그린다(React가 이스케이프). dangerouslySetInnerHTML 금지

const MAX_LENGTH = 300;
const PAGE_SIZE = 100;

/**
 * @param {number} taskId
 * @param {(total: number) => void} [onCountChange] 댓글 수가 정해지거나 바뀔 때마다 호출
 */
export default function TaskComments({ taskId, onCountChange }) {
  const toast = useToast();
  // 내 댓글에만 수정·삭제 버튼 — 로그인한 사용자는 인증 Context에서 읽는다(탭 틀이 myId를 넘기지 않음)
  const myId = useAuth().user?.id;

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(null); // null = 아직 모름
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  const [draft, setDraft] = useState("");
  const [posting, setPosting] = useState(false);
  const [postError, setPostError] = useState(null);

  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState("");
  const [savingId, setSavingId] = useState(null);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let ignore = false;
    listComments(taskId, { page: 1, size: PAGE_SIZE })
      .then((data) => {
        if (ignore) return;
        setItems(data.items);
        setTotal(data.total);
        setPage(1);
      })
      .catch(() => !ignore && setLoadFailed(true))
      .finally(() => !ignore && setLoading(false));
    return () => {
      ignore = true;
    };
  }, [taskId]);

  useEffect(() => {
    if (total !== null) onCountChange?.(total);
  }, [total, onCountChange]);

  const removeLocal = (commentId) => {
    setItems((prev) => prev.filter((c) => c.id !== commentId));
    setTotal((prev) => Math.max(0, (prev ?? 1) - 1));
  };

  // 수정·삭제 실패 공통 처리. 401은 Axios 인터셉터가 처리한다.
  const handleActionError = (error, commentId) => {
    const data = error.response?.data;
    if (error.response?.status === 401) return;
    if (data?.code === "COMMENT_NOT_FOUND") {
      toast.error("이미 삭제된 댓글입니다");
      removeLocal(commentId);
      return;
    }
    toast.error(data?.message ?? "잠시 후 다시 시도해 주세요");
  };

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const data = await listComments(taskId, {
        page: page + 1,
        size: PAGE_SIZE,
      });
      // 그 사이 지워지거나 추가된 댓글 때문에 겹칠 수 있어 id로 거른다
      setItems((prev) => {
        const seen = new Set(prev.map((c) => c.id));
        return [...prev, ...data.items.filter((c) => !seen.has(c.id))];
      });
      setTotal(data.total);
      setPage(page + 1);
    } catch {
      toast.error("댓글을 불러오지 못했습니다");
    } finally {
      setLoadingMore(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!isValid(draft) || posting) return;
    setPosting(true);
    setPostError(null);
    try {
      const created = await createComment(taskId, draft);
      // 모두 불러온 상태면 맨 아래에 붙인다(오래된 순 → 새 댓글은 마지막)
      setItems((prev) =>
        prev.length >= (total ?? 0) ? [...prev, created] : prev,
      );
      setTotal((prev) => (prev ?? 0) + 1);
      setDraft("");
    } catch (error) {
      const data = error.response?.data;
      if (error.response?.status === 422) {
        setPostError(data?.errors?.[0]?.message ?? data?.message);
      } else if (error.response?.status !== 401) {
        toast.error(data?.message ?? "잠시 후 다시 시도해 주세요");
      }
    } finally {
      setPosting(false);
    }
  };

  const startEdit = (comment) => {
    setEditingId(comment.id);
    setEditDraft(comment.content);
  };

  const saveEdit = async (comment) => {
    if (!isValid(editDraft) || savingId !== null) return;
    setSavingId(comment.id);
    try {
      const updated = await updateComment(comment.id, editDraft);
      setItems((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
      setEditingId(null);
    } catch (error) {
      handleActionError(error, comment.id);
      if (error.response?.data?.code === "COMMENT_NOT_FOUND")
        setEditingId(null);
    } finally {
      setSavingId(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget || deleting) return;
    setDeleting(true);
    try {
      await deleteComment(deleteTarget.id);
      removeLocal(deleteTarget.id);
    } catch (error) {
      handleActionError(error, deleteTarget.id);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {loading ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
          <span className="sr-only">불러오는 중입니다</span>
        </div>
      ) : loadFailed ? (
        <p className="text-sm text-neutral-500">댓글을 불러오지 못했습니다</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-neutral-500">아직 댓글이 없습니다</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {items.map((comment) => {
            const mine = comment.user.id === myId;
            const editing = editingId === comment.id;
            return (
              <li key={comment.id} className="flex gap-3">
                <Avatar user={comment.user} size="sm" className="shrink-0" />
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="flex flex-wrap items-center gap-x-2 text-xs">
                    <span className="font-semibold text-neutral-900">
                      {comment.user.name}
                    </span>
                    <span className="text-neutral-400">
                      {formatDateTime(comment.created_at)}
                    </span>
                    {comment.updated_at !== comment.created_at && (
                      <span className="text-neutral-400">수정됨</span>
                    )}
                    {mine && !editing && (
                      <span className="ml-auto flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => startEdit(comment)}
                        >
                          수정
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteTarget(comment)}
                        >
                          삭제
                        </Button>
                      </span>
                    )}
                  </div>
                  {editing ? (
                    <div className="flex flex-col gap-2">
                      <CountedTextarea
                        label="댓글 수정"
                        autoFocus
                        value={editDraft}
                        onChange={setEditDraft}
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => saveEdit(comment)}
                          loading={savingId === comment.id}
                          disabled={!isValid(editDraft)}
                        >
                          저장
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setEditingId(null)}
                          disabled={savingId === comment.id}
                        >
                          취소
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm break-words whitespace-pre-wrap text-neutral-800">
                      {comment.content}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {!loading && total !== null && items.length < total && (
        <Button
          variant="secondary"
          size="sm"
          onClick={loadMore}
          loading={loadingMore}
          className="self-center"
        >
          댓글 더 보기
        </Button>
      )}

      <form onSubmit={submit} className="flex flex-col gap-2">
        <CountedTextarea
          label="댓글 입력"
          placeholder="댓글을 입력해 주세요"
          value={draft}
          onChange={(value) => {
            setDraft(value);
            setPostError(null);
          }}
          error={postError}
        />
        <Button
          type="submit"
          size="sm"
          loading={posting}
          disabled={!isValid(draft)}
          className="self-end"
        >
          등록
        </Button>
      </form>

      <ConfirmDialog
        open={deleteTarget !== null}
        title="댓글을 삭제하시겠습니까?"
        message="삭제한 댓글은 되돌릴 수 없습니다"
        confirmLabel="삭제"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}

// 서버와 같게 앞뒤 공백을 빼고 코드 포인트로 센다(#49)
const lengthOf = (value) => charCount(value.trim());
const isValid = (value) => {
  const n = lengthOf(value);
  return n > 0 && n <= MAX_LENGTH;
};

function CountedTextarea({
  label,
  value,
  onChange,
  placeholder,
  autoFocus,
  error,
}) {
  const n = lengthOf(value);
  const over = n > MAX_LENGTH;
  return (
    <div className="flex flex-col gap-1">
      <textarea
        aria-label={label}
        aria-invalid={over || Boolean(error)}
        autoFocus={autoFocus}
        rows={3}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "w-full resize-y rounded-lg border bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-2 focus:-outline-offset-1 focus:outline-primary",
          over || error ? "border-danger" : "border-neutral-300",
        )}
      />
      <div className="flex items-start justify-between gap-2 text-xs">
        <span className="text-danger">{error}</span>
        <span
          className={cn("shrink-0", over ? "text-danger" : "text-neutral-400")}
        >
          {n}/{MAX_LENGTH}
        </span>
      </div>
    </div>
  );
}
