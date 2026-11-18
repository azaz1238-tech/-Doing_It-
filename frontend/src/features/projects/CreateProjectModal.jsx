import { useId, useState } from "react";
import Button from "../../core/ui/Button";
import Input from "../../core/ui/Input";
import Modal from "../../core/ui/Modal";
import { useToast } from "../../core/ui/useToast";
import { createProject } from "./api";
import { countChars, NAME_ERROR, NAME_MAX, PERIOD_ERROR } from "./projectRules";

// S3 새 프로젝트 모달 — PRJ-01 · UI-DESIGN S3 · 시안2 "새 프로젝트 모달"

/**
 * @param {() => void} onClose
 * @param {(project: object) => void} onCreated 만들기 성공 → 목록 화면이 새 프로젝트 S4로 보낸다
 *
 * 열 때마다 새 입력으로 시작하도록, 목록에서 열려 있을 때만 그린다({open && <CreateProjectModal/>}).
 */
export default function CreateProjectModal({ onClose, onCreated }) {
  const formId = useId();
  const toast = useToast();
  const [form, setForm] = useState({
    name: "",
    description: "",
    startDate: "",
    endDate: "",
  });
  const [nameTouched, setNameTouched] = useState(false);
  const [serverErrors, setServerErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const nameLength = countChars(form.name.trim());
  const nameValid = nameLength >= 1 && nameLength <= NAME_MAX;
  // "YYYY-MM-DD" 문자열은 그대로 비교해도 날짜 순서와 같다
  const periodValid =
    !form.startDate || !form.endDate || form.endDate >= form.startDate;
  const isDirty = Object.values(form).some((value) => value !== "");

  // 이름 오류: 칸을 떠난 뒤(비움) 또는 31자를 넘긴 순간 보인다. 날짜 오류는 입력하는 순간 (시안2 "바뀐 점")
  const nameError =
    (nameTouched || nameLength > NAME_MAX) && !nameValid
      ? NAME_ERROR
      : serverErrors.name;
  const endDateError = periodValid ? serverErrors.end_date : PERIOD_ERROR;

  // key = 폼 상태 이름, field = 서버 422 errors의 field 이름
  const set = (key, field) => (e) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
    setServerErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!nameValid || !periodValid || submitting) {
      setNameTouched(true);
      return;
    }
    setSubmitting(true);
    try {
      const project = await createProject({
        name: form.name.trim(),
        description: form.description.trim(),
        startDate: form.startDate,
        endDate: form.endDate,
      });
      toast.success("프로젝트를 만들었습니다");
      onCreated(project);
    } catch (error) {
      const body = error.response?.data;
      if (body?.code === "VALIDATION_ERROR" && body.errors?.length) {
        // 422 errors[{field, message}]를 해당 칸 아래에 보여 준다.
        setServerErrors(
          Object.fromEntries(body.errors.map((er) => [er.field, er.message])),
        );
      } else {
        toast.error(body?.message ?? "잠시 후 다시 시도해 주세요");
      }
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title="새 프로젝트"
      subtitle="만든 사람이 OWNER가 됩니다"
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
            disabled={!nameValid || !periodValid}
          >
            만들기
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={submit} className="flex flex-col gap-4">
        <Input
          label="이름"
          required
          autoFocus
          maxCount={NAME_MAX} // PRJ-01-b "입력칸에 남은 글자 수가 보인다" → n/30
          value={form.name}
          onChange={set("name", "name")}
          onBlur={() => setNameTouched(true)}
          error={nameError}
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
            onChange={set("description", "description")}
            placeholder="어떤 목표의 프로젝트인지 적어 주세요 (선택)"
            className="w-full resize-y rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-2 focus:-outline-offset-1 focus:outline-primary"
          />
          {serverErrors.description && (
            <p className="text-xs text-danger">{serverErrors.description}</p>
          )}
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="시작일"
            type="date"
            value={form.startDate}
            onChange={set("startDate", "start_date")}
            error={serverErrors.start_date}
          />
          <Input
            label="종료일"
            type="date"
            value={form.endDate}
            onChange={set("endDate", "end_date")}
            error={endDateError}
          />
        </div>
      </form>
    </Modal>
  );
}
