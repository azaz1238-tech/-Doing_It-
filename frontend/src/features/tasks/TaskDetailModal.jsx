import { useCallback, useEffect, useRef, useState } from "react";
import {
  useLocation,
  useNavigate,
  useOutletContext,
  useParams,
} from "react-router";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import ConfirmDialog from "../../core/ui/ConfirmDialog";
import { ChevronDownIcon, LockIcon } from "../../core/ui/icons";
import Input from "../../core/ui/Input";
import Modal from "../../core/ui/Modal";
import Skeleton from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import {
  daysBetween,
  formatDateTime,
  formatDateWithWeekday,
  todayKst,
} from "../../core/utils/date";
import MemberSelect from "../projects/MemberSelect";
import { deleteTask, getTask, updateTask } from "./api";
import DueLabel from "./DueLabel";
import { getTaskPermissions } from "./permissions";
import PriorityBadge from "./PriorityBadge";
import StatusSelect from "./StatusSelect";
import { charCount, PRIORITIES, STATUSES } from "./taskDisplay";

// S6 업무 상세 모달 — UI-DESIGN §4 S6, TASK-02·03·06, SPEC TASK-06-a~e
// 주소 /projects/:id/tasks/:taskId — 보드(S4) 위에 열리고, 새로고침·공유해도 같은 창이 열린다(TASK-06-a).
// - 속성(상태·우선순위·담당자·마감일)은 고르는 즉시 그 필드 1개만 PATCH → 이력도 1행
// - 제목·설명은 눌러서 수정 → 저장/취소 (이력 대상 아님, LOG-01)
// - 댓글·변경 이력 탭은 P1이라 P0에서는 비워 둔다

const TITLE_MAX = 30;
const TITLE_ERROR = "업무 제목은 1~30자로 입력해 주세요"; // SPEC TASK-01-b
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"]; // SPEC TASK-04-b
const TO_PARTICLE = { TODO: "로", IN_PROGRESS: "으로", DONE: "로" };

// 업무가 바뀌면 상태를 새로 시작하도록 taskId를 key로 준다.
export default function TaskDetailModal() {
  const { taskId } = useParams();
  return <TaskDetail key={taskId} taskId={taskId} />;
}

function TaskDetail({ taskId }) {
  const navigate = useNavigate();
  const toast = useToast();
  // BoardPage가 Outlet context로 넘긴다.
  const { projectId, project, members, user, onTaskChanged } =
    useOutletContext();

  const [task, setTask] = useState(null);
  const [saving, setSaving] = useState(null); // 저장 중인 필드 이름
  const [titleDraft, setTitleDraft] = useState(null); // null = 보기 모드
  const [descDraft, setDescDraft] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  // 삭제 확인을 빠르게 두 번 누르면 두 번째 DELETE가 404로 돌아온다 → ref로 바로 막는다(D7-01).
  const deletingRef = useRef(false);

  // 닫아도 보드의 검색·필터(주소 쿼리)는 그대로 둔다(TASK-07).
  const { search } = useLocation();
  const close = useCallback(
    () => navigate(`/projects/${projectId}${search}`),
    [navigate, projectId, search],
  );

  // 업무 없음(삭제됐거나 잘못된 주소) → 안내 후 보드로. 비멤버 403은 보드가 안내 화면을 띄운다.
  const handleLoadError = useCallback(
    (error) => {
      const data = error.response?.data;
      if (data?.code === "NOT_PROJECT_MEMBER") return close();
      toast.error(data?.message ?? "업무를 불러오지 못했습니다");
      close();
    },
    [close, toast],
  );

  useEffect(() => {
    let ignore = false;
    // 주소의 id가 숫자가 아니면 서버에 묻지 않고 "없는 업무"로 처리한다(서버는 422를 준다).
    // 개발 모드(StrictMode)는 effect를 두 번 돌리므로, 한 박자 미뤄 정리(cleanup) 때 취소되게 한다 → 토스트 1번.
    if (!/^\d+$/.test(taskId)) {
      const timer = setTimeout(() => {
        toast.error("업무를 찾을 수 없습니다");
        close();
      });
      return () => clearTimeout(timer);
    }
    getTask(taskId)
      .then((data) => !ignore && setTask(data))
      .catch((error) => !ignore && handleLoadError(error));
    return () => {
      ignore = true;
    };
  }, [taskId, handleLoadError, toast, close]);

  // 바꾼 필드만 보낸다. 성공하면 응답(Task)으로 화면을 바꾸고 보드도 다시 불러온다.
  const save = async (field, patch, successMessage = "저장했습니다") => {
    setSaving(field);
    try {
      const updated = await updateTask(task.id, patch);
      setTask(updated);
      onTaskChanged();
      toast.success(successMessage);
      return true;
    } catch (error) {
      handleSaveError(error);
      return false;
    } finally {
      setSaving(null);
    }
  };

  const handleSaveError = (error) => {
    const data = error.response?.data;
    if (data?.code === "TASK_NOT_FOUND") {
      // 그 사이 다른 사람이 지움
      toast.error(data.message);
      onTaskChanged();
      close();
    } else if (data?.code === "FORBIDDEN") {
      // 그 사이 권한이 바뀜(담당 해제 등) → 최신 값으로 🔒를 다시 그린다.
      toast.error(data.message);
      getTask(task.id).then(setTask, () => {});
    } else if (data?.code === "VALIDATION_ERROR") {
      toast.error(data.errors?.[0]?.message ?? data.message);
    } else {
      // ASSIGNEE_NOT_MEMBER 등은 서버 message를 그대로(UI-DESIGN §6.5)
      toast.error(data?.message ?? "저장하지 못했습니다");
    }
  };

  const copyLink = () => {
    navigator.clipboard
      ?.writeText(window.location.href)
      .then(() => toast.success("링크를 복사했습니다"))
      .catch(() => toast.error("링크를 복사하지 못했습니다"));
  };

  const confirmDelete = async () => {
    if (deletingRef.current) return;
    deletingRef.current = true;
    setDeleting(true);
    try {
      await deleteTask(task.id);
      toast.success("업무를 삭제했습니다");
      onTaskChanged();
      close();
    } catch (error) {
      deletingRef.current = false;
      setDeleting(false);
      setConfirmOpen(false);
      handleSaveError(error);
    }
  };

  const modalTitle = project ? `${project.name} › 업무 상세` : "업무 상세";

  if (!task) {
    return (
      <Modal open onClose={close} title={modalTitle} size="lg">
        <div aria-busy="true" className="flex flex-col gap-3 py-2">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-1/2" />
          <span className="sr-only">불러오는 중입니다</span>
        </div>
      </Modal>
    );
  }

  // 프로젝트(내 역할)를 받기 전에는 모두 읽기 전용으로 둔다.
  const perm =
    project && user
      ? getTaskPermissions(task, project.my_role, user.id)
      : { canEdit: false, canChangeStatus: false, canDelete: false };

  // 현재 담당자가 멤버 목록에 없으면(그 사이 프로젝트에서 빠짐 등) 그 사람도 넣어 지금 값이 보이게 한다.
  const memberOptions =
    task.assignee && !members.some((m) => m.user_id === task.assignee.id)
      ? [
          ...members,
          {
            user_id: task.assignee.id,
            login_id: task.assignee.login_id,
            name: task.assignee.name,
          },
        ]
      : members;

  const trimmedTitle = titleDraft?.trim() ?? "";
  const titleLength = charCount(trimmedTitle);
  const titleValid = titleLength >= 1 && titleLength <= TITLE_MAX;
  const isDirty =
    (titleDraft !== null && titleDraft !== task.title) ||
    (descDraft !== null && descDraft !== (task.description ?? ""));

  const saveTitle = async (e) => {
    e.preventDefault();
    if (!titleValid) return;
    if (trimmedTitle === task.title) return setTitleDraft(null);
    if (await save("title", { title: trimmedTitle })) setTitleDraft(null);
  };

  const saveDescription = async () => {
    // 비우면 null로 보낸다(API-SPEC §5.4: 문자열 또는 null)
    const next = descDraft.trim() === "" ? null : descDraft;
    if (next === (task.description ?? null)) return setDescDraft(null);
    if (await save("description", { description: next })) setDescDraft(null);
  };

  return (
    <Modal open onClose={close} title={modalTitle} size="lg" isDirty={isDirty}>
      <div className="mb-4 flex justify-end gap-1">
        <Button variant="ghost" size="sm" onClick={copyLink}>
          링크 복사
        </Button>
        {/* 삭제 버튼은 OWNER·작성자에게만 보인다. 권한 판단은 백엔드가 한다 */}
        {perm.canDelete && (
          <Button
            variant="ghost"
            size="sm"
            className="text-danger! hover:bg-danger-soft!"
            onClick={() => setConfirmOpen(true)}
          >
            삭제
          </Button>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-[1fr_15rem]">
        {/* 왼쪽: 제목·설명 */}
        <div className="flex min-w-0 flex-col gap-5">
          {titleDraft !== null ? (
            <form onSubmit={saveTitle} className="flex flex-col gap-2">
              <Input
                aria-label="제목"
                autoFocus
                maxCount={TITLE_MAX}
                value={titleDraft}
                error={titleValid ? undefined : TITLE_ERROR}
                onChange={(e) => setTitleDraft(e.target.value)}
              />
              <div className="flex gap-2">
                <Button
                  type="submit"
                  size="sm"
                  disabled={!titleValid}
                  loading={saving === "title"}
                >
                  저장
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setTitleDraft(null)}
                >
                  취소
                </Button>
              </div>
            </form>
          ) : (
            <h3 className="text-lg font-bold break-words text-neutral-900">
              <EditableText
                editable={perm.canEdit}
                onEdit={() => setTitleDraft(task.title)}
                label="제목 수정"
              >
                {task.title}
              </EditableText>
            </h3>
          )}

          <section className="flex flex-col gap-1.5">
            <h4 className="text-xs font-semibold text-neutral-500">설명</h4>
            {descDraft !== null ? (
              <div className="flex flex-col gap-2">
                <textarea
                  aria-label="설명"
                  autoFocus
                  rows={5}
                  value={descDraft}
                  onChange={(e) => setDescDraft(e.target.value)}
                  className="w-full resize-y rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-2 focus:-outline-offset-1 focus:outline-primary"
                />
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={saveDescription}
                    loading={saving === "description"}
                  >
                    저장
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setDescDraft(null)}
                  >
                    취소
                  </Button>
                </div>
              </div>
            ) : (
              <EditableText
                editable={perm.canEdit}
                onEdit={() => setDescDraft(task.description ?? "")}
                label="설명 수정"
              >
                {/* 사용자 입력은 텍스트로만 넣는다(dangerouslySetInnerHTML 금지) */}
                <span
                  className={cn(
                    "block min-h-10 break-words whitespace-pre-wrap",
                    task.description ? "text-neutral-700" : "text-neutral-400",
                  )}
                >
                  {task.description ||
                    (perm.canEdit ? "설명을 추가해 주세요" : "설명이 없습니다")}
                </span>
              </EditableText>
            )}
          </section>
        </div>

        {/* 오른쪽: 속성 — 고르는 즉시 저장 */}
        <dl className="flex flex-col gap-4 rounded-lg bg-neutral-50 p-4">
          <Field label="상태">
            <StatusSelect
              value={task.status}
              readOnly={!perm.canChangeStatus}
              disabled={saving === "status"}
              // 세로 배치(dd) 안에서 가로로 늘어나지 않게 — ▾가 드롭다운 옆에 붙는다
              className="self-start"
              onChange={(status) =>
                save(
                  "status",
                  { status },
                  `상태를 '${STATUSES[status].label}'${TO_PARTICLE[status]} 변경했습니다`,
                )
              }
            />
          </Field>

          <Field label="우선순위">
            {perm.canEdit ? (
              <NativeSelect
                aria-label="우선순위"
                value={task.priority}
                disabled={saving === "priority"}
                onChange={(e) => save("priority", { priority: e.target.value })}
              >
                {PRIORITY_ORDER.map((key) => (
                  <option key={key} value={key}>
                    {PRIORITIES[key].label}
                  </option>
                ))}
              </NativeSelect>
            ) : (
              <Locked>
                <PriorityBadge priority={task.priority} />
              </Locked>
            )}
          </Field>

          <Field label="담당자">
            {perm.canEdit ? (
              <MemberSelect
                label=""
                members={memberOptions}
                value={task.assignee?.id ?? null}
                disabled={saving === "assignee_id"}
                onChange={(id) => save("assignee_id", { assignee_id: id })}
              />
            ) : (
              <Locked>
                <span className="flex items-center gap-2 text-neutral-700">
                  <Avatar user={task.assignee} size="sm" />
                  {task.assignee?.name ?? "담당자 없음"}
                </span>
              </Locked>
            )}
          </Field>

          <Field label="마감일">
            {perm.canEdit ? (
              <input
                type="date"
                aria-label="마감일"
                value={task.due_date ?? ""}
                disabled={saving === "due_date"}
                // 비우면 마감일 해제(null). 지난 날짜도 허용(API-SPEC §5.4)
                onChange={(e) =>
                  save("due_date", { due_date: e.target.value || null })
                }
                className="h-9 w-full rounded-lg border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-2 focus:-outline-offset-1 focus:outline-primary disabled:opacity-60"
              />
            ) : (
              <Locked>
                <span className="text-neutral-700">
                  {task.due_date
                    ? formatDateWithWeekday(task.due_date)
                    : "마감 없음"}
                </span>
              </Locked>
            )}
            {/* 입력칸·읽기 전용 줄에 날짜가 이미 있으므로, 배지는 지연·임박(오늘 ~ +3일)일 때만 보인다.
                먼 날짜까지 DueLabel을 그리면 "11/25"가 한 번 더 보인다(최진영 #53 제보). */}
            {task.due_date && daysBetween(todayKst(), task.due_date) <= 3 && (
              <DueLabel
                dueDate={task.due_date}
                status={task.status}
                className="mt-1.5 self-start"
              />
            )}
          </Field>

          <div className="border-t border-neutral-200 pt-4 text-xs text-neutral-500">
            <p>
              작성자{" "}
              <span className="font-medium text-neutral-700">
                {task.created_by.name}
              </span>
            </p>
            <p className="mt-1">만든 날 {formatDateTime(task.created_at)}</p>
          </div>
        </dl>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="이 업무를 삭제할까요?" // SPEC TASK-06-c 문구 그대로
        message={`'${task.title}' 업무가 삭제됩니다.\n변경 이력은 남습니다`}
        confirmLabel="삭제"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setConfirmOpen(false)}
      />
    </Modal>
  );
}

function Field({ label, children }) {
  return (
    <div className="flex flex-col">
      <dt className="mb-1.5 text-xs font-semibold text-neutral-500">{label}</dt>
      <dd className="flex flex-col">{children}</dd>
    </div>
  );
}

// 권한 없는 항목: 값 + 🔒 (UI-DESIGN S6 권한표)
function Locked({ children }) {
  return (
    <span
      className="inline-flex items-center gap-2"
      title="이 항목을 바꿀 권한이 없습니다"
    >
      {children}
      <LockIcon size={12} className="text-neutral-400" />
      <span className="sr-only">(변경 권한 없음)</span>
    </span>
  );
}

// 제목·설명: 수정할 수 있으면 눌러서 편집, 아니면 그냥 글자.
// <button> 안에는 글자(span)만 넣는다(h3·p는 버튼 밖에 둔다).
function EditableText({ editable, onEdit, label, children }) {
  if (!editable) return <span className="block">{children}</span>;
  return (
    <button
      type="button"
      onClick={onEdit}
      title={label}
      className="-mx-2 block w-[calc(100%+1rem)] rounded-lg px-2 py-1 text-left hover:bg-neutral-100 focus-visible:outline-2 focus-visible:outline-primary"
    >
      {children}
    </button>
  );
}

function NativeSelect({ className, children, ...rest }) {
  return (
    <span className={cn("relative flex", className)}>
      <select
        {...rest}
        className="h-9 w-full appearance-none rounded-lg border border-neutral-300 bg-white pr-9 pl-3 text-sm text-neutral-900 focus:outline-2 focus:-outline-offset-1 focus:outline-primary disabled:opacity-60"
      >
        {children}
      </select>
      <ChevronDownIcon className="pointer-events-none absolute inset-y-0 right-3 my-auto text-neutral-500" />
    </span>
  );
}
