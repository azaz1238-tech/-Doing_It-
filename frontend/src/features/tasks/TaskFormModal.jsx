import { useId, useRef, useState } from "react";
import Button from "../../core/ui/Button";
import Input from "../../core/ui/Input";
import Modal from "../../core/ui/Modal";
import { useToast } from "../../core/ui/useToast";
import { cn } from "../../core/utils/cn";
import { todayKst } from "../../core/utils/date";
import MemberSelect from "../projects/MemberSelect";
import { createTask } from "./api";
import { charCount, PRIORITIES } from "./taskDisplay";

// S5 업무 등록 모달 — UI-DESIGN §4 S5, TASK-01·03·04

const TITLE_MAX = 30;
const TITLE_ERROR = "업무 제목은 1~30자로 입력해 주세요"; // SPEC TASK-01-b
// 세그먼트 순서는 SPEC TASK-04-b("낮음·보통·높음·긴급")를 따른다.
const PRIORITY_ORDER = ["LOW", "MEDIUM", "HIGH", "URGENT"];

const EMPTY_FORM = {
  title: "",
  description: "",
  priority: "MEDIUM", // TASK-04-a: 고르지 않으면 보통
  assigneeId: null,
  dueDate: "",
};

/**
 * @param {number|string} projectId
 * @param {() => void} onClose
 * @param {(task: object) => void} onCreated 등록 성공 → 보드가 '할 일' 컬럼을 다시 불러온다
 * @param {Array} members 보드(S4)에서 받은 멤버 목록을 재사용한다
 * @param {() => void} onMembersStale 400 ASSIGNEE_NOT_MEMBER → 멤버 목록 다시 조회
 *
 * 열 때마다 새 입력으로 시작하도록, 보드에서 열려 있을 때만 그린다({open && <TaskFormModal/>}).
 */
export default function TaskFormModal({
  projectId,
  onClose,
  onCreated,
  members,
  onMembersStale,
}) {
  const toast = useToast();
  const formId = useId();
  const [form, setForm] = useState(EMPTY_FORM);
  const [titleTouched, setTitleTouched] = useState(false);
  const [serverErrors, setServerErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  // 빠르게 두 번 누르면 상태(submitting)가 바뀌기 전에 두 번째 제출이 들어온다 → ref로 바로 막는다(D7-01).
  const submittingRef = useRef(false);

  const set = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    // 고친 필드의 서버 오류는 지운다.
    setServerErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const trimmedTitle = form.title.trim();
  const titleLength = charCount(trimmedTitle);
  const titleValid = titleLength >= 1 && titleLength <= TITLE_MAX;
  // 처음 열었을 때 빈 제목에 오류를 띄우지 않는다. 입력을 시작했거나 30자를 넘으면 보인다.
  const titleError =
    serverErrors.title ??
    ((titleTouched || form.title.length > 0) && !titleValid
      ? TITLE_ERROR
      : undefined);

  const isPast = form.dueDate !== "" && form.dueDate < todayKst();
  const isDirty =
    form.title !== "" ||
    form.description !== "" ||
    form.priority !== EMPTY_FORM.priority ||
    form.assigneeId !== null ||
    form.dueDate !== "";

  const submit = async (e) => {
    e.preventDefault();
    if (submittingRef.current) return;
    if (!titleValid) {
      setTitleTouched(true);
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    try {
      // 비어 있는 선택 필드는 보내지 않는다(API-SPEC §5.4: 모두 선택, priority 기본 MEDIUM).
      const body = { title: trimmedTitle, priority: form.priority };
      if (form.description.trim()) body.description = form.description;
      if (form.assigneeId != null) body.assignee_id = form.assigneeId;
      if (form.dueDate) body.due_date = form.dueDate;

      const created = await createTask(projectId, body);
      toast.success("업무를 추가했습니다");
      onCreated(created);
    } catch (error) {
      handleError(error);
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  const handleError = (error) => {
    const data = error.response?.data;
    if (data?.code === "ASSIGNEE_NOT_MEMBER") {
      // 그 사이 멤버가 제거된 경우 — 담당자 칸에 오류를 띄우고 멤버 목록을 새로 받는다.
      setServerErrors({ assigneeId: data.message });
      onMembersStale?.();
    } else if (data?.code === "VALIDATION_ERROR" && data.errors) {
      // 422 errors[{field, message}]를 해당 칸 아래에 보여 준다.
      const FIELD = {
        title: "title",
        description: "description",
        assignee_id: "assigneeId",
        due_date: "dueDate",
        priority: "priority",
      };
      setServerErrors(
        Object.fromEntries(
          data.errors.map((err) => [
            FIELD[err.field] ?? err.field,
            err.message,
          ]),
        ),
      );
    } else {
      // 모르는 code는 서버 message를 그대로 보여 준다(UI-DESIGN §6.5).
      toast.error(data?.message ?? "업무를 추가하지 못했습니다");
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="새 업무"
      subtitle="'할 일' 칸에 추가됩니다"
      isDirty={isDirty}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            취소
          </Button>
          <Button
            type="submit"
            form={formId}
            loading={submitting}
            disabled={!titleValid}
          >
            업무 추가
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={submit} className="flex flex-col gap-4">
        <Input
          label="제목"
          required
          autoFocus
          maxCount={TITLE_MAX}
          value={form.title}
          error={titleError}
          onChange={(e) => set("title", e.target.value)}
          onBlur={() => setTitleTouched(true)}
          placeholder="무엇을 해야 하나요?"
        />

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor={`${formId}-desc`}
            className="font-semibold text-neutral-900"
          >
            설명
          </label>
          <textarea
            id={`${formId}-desc`}
            rows={3}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            className="w-full resize-y rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-2 focus:-outline-offset-1 focus:outline-primary"
            placeholder="자세한 내용을 적어 주세요 (선택)"
          />
          {serverErrors.description && (
            <p className="text-xs text-danger">{serverErrors.description}</p>
          )}
        </div>

        <fieldset className="flex flex-col gap-1.5">
          <legend className="mb-1.5 font-semibold text-neutral-900">
            우선순위
          </legend>
          <div
            role="radiogroup"
            aria-label="우선순위"
            className="grid grid-cols-4 gap-1 rounded-lg bg-neutral-100 p-1"
          >
            {PRIORITY_ORDER.map((key) => {
              const selected = form.priority === key;
              return (
                <button
                  key={key}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => set("priority", key)}
                  className={cn(
                    "h-8 rounded-md text-sm font-medium transition-colors",
                    "focus-visible:outline-2 focus-visible:outline-primary",
                    selected
                      ? cn("bg-white shadow-sm", PRIORITIES[key].text)
                      : "text-neutral-500 hover:text-neutral-700",
                  )}
                >
                  {PRIORITIES[key].label}
                </button>
              );
            })}
          </div>
          {serverErrors.priority && (
            <p className="text-xs text-danger">{serverErrors.priority}</p>
          )}
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <MemberSelect
            members={members}
            value={form.assigneeId}
            onChange={(id) => set("assigneeId", id)}
            error={serverErrors.assigneeId}
          />
          <Input
            label="마감일"
            type="date"
            value={form.dueDate}
            onChange={(e) => set("dueDate", e.target.value)}
            error={serverErrors.dueDate}
            // 지난 날짜도 허용한다(API-SPEC §5.4). 등록하면 지연으로 보인다(TASK-01-c).
            hint={
              isPast ? "지난 날짜입니다. 지연 업무로 표시됩니다" : undefined
            }
          />
        </div>
      </form>
    </Modal>
  );
}
