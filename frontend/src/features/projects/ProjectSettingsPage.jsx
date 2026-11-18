import { useEffect, useId, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import Button from "../../core/ui/Button";
import ConfirmDialog from "../../core/ui/ConfirmDialog";
import EmptyState from "../../core/ui/EmptyState";
import { FolderIcon, LockIcon } from "../../core/ui/icons";
import Input from "../../core/ui/Input";
import Skeleton from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import { formatPeriod } from "../../core/utils/date";
import { listTasks } from "../tasks/api";
import { deleteProject, getProject, listMembers, updateProject } from "./api";
import ProjectHeader from "./ProjectHeader";
import { countChars, NAME_ERROR, NAME_MAX, PERIOD_ERROR } from "./projectRules";

// S7 프로젝트 설정 — UI-DESIGN §4 S7 · PRJ-03(수정·삭제) · US-08
// 한 페이지에 세 구역(프로젝트 정보 · 멤버 · 프로젝트 삭제). 멤버 구역은 T-F3-05에서 추가한다.
// 버튼 숨김은 편의 기능이다. 권한 판단은 백엔드가 한다(MEMBER가 다른 방법으로 시도하면 403).

// 페이지 진입 오류 → 안내 화면 (UI-DESIGN S8). 버튼 동작 중 403 FORBIDDEN은 토스트만 띄운다.
// TODO(T-F0-14): 김서현 ErrorPage가 나오면 BoardPage와 함께 교체
function pageErrorOf(error) {
  const res = error.response;
  if (res?.data?.code === "NOT_PROJECT_MEMBER") return "403";
  if (res?.status === 404) return "404";
  return null;
}

// 422 errors[{field, message}] → { field: message }
function fieldErrorsOf(error) {
  const body = error.response?.data;
  if (body?.code !== "VALIDATION_ERROR" || !body.errors?.length) return null;
  return Object.fromEntries(body.errors.map((er) => [er.field, er.message]));
}

// 프로젝트가 바뀌면 상태를 모두 새로 시작하도록 id를 key로 준다(BoardPage와 같음).
export default function ProjectSettingsPage() {
  const { id } = useParams();
  return <Settings key={id} projectId={id} />;
}

function Settings({ projectId }) {
  const toast = useToast();
  const [project, setProject] = useState(null);
  const [members, setMembers] = useState(null);
  const [pageError, setPageError] = useState(null); // "403" | "404" | null

  const handleError = (error, fallback) => {
    const kind = pageErrorOf(error);
    if (kind) setPageError(kind);
    // 모르는 code는 서버 message를 그대로 보여 준다(UI-DESIGN §6.5).
    else toast.error(error.response?.data?.message ?? fallback);
  };

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
    // 멤버는 헤더 아바타용. 실패하면 아바타만 숨긴다(권한·없음 안내는 getProject 쪽이 맡는다).
    listMembers(projectId)
      .then((data) => !ignore && setMembers(data.items))
      .catch(() => {});
    return () => {
      ignore = true;
    };
  }, [projectId, toast]);

  if (pageError) {
    const forbidden = pageError === "403";
    return (
      <EmptyState
        icon={forbidden ? LockIcon : FolderIcon}
        // PRJ-07-a: 비멤버에게는 프로젝트 이름도 보이지 않는다.
        title={
          forbidden ? "접근 권한이 없습니다" : "프로젝트를 찾을 수 없습니다"
        }
        description={
          forbidden
            ? "이 프로젝트의 멤버만 볼 수 있습니다"
            : "삭제되었거나 주소가 올바르지 않습니다"
        }
        action={
          <Link
            to="/projects"
            className="inline-flex h-9 items-center rounded-lg bg-primary px-4 text-sm font-medium text-white hover:bg-primary-hover"
          >
            프로젝트 목록으로
          </Link>
        }
      />
    );
  }

  // 화면 편의용 구분. 실제 권한은 백엔드가 판단한다.
  const isOwner = project?.my_role === "OWNER";

  return (
    <div className="flex flex-col gap-6">
      <ProjectHeader project={project} members={members} active="settings" />

      {project ? (
        <>
          {/* 저장하면 updated_at이 바뀌어 폼이 저장된 값으로 다시 시작한다 */}
          <InfoSection
            key={project.updated_at}
            project={project}
            editable={isOwner}
            onSaved={setProject}
            onError={handleError}
          />
          {/* MEMBER에게는 삭제 구역을 숨긴다(UI-DESIGN S7) */}
          {isOwner && <DeleteSection project={project} onError={handleError} />}
        </>
      ) : (
        <div aria-hidden="true" className="flex flex-col gap-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-40 w-full max-w-xl" />
        </div>
      )}
    </div>
  );
}

function Section({ title, children }) {
  return (
    <section className="max-w-xl rounded-xl border border-neutral-200 bg-white p-6">
      {/* TODO(Figma): S7 구역 제목은 시안 확정 전 추정값 */}
      <h2 className="mb-4 text-lg font-bold text-neutral-900">{title}</h2>
      {children}
    </section>
  );
}

// 프로젝트 정보 — OWNER는 수정 + 저장, MEMBER는 읽기 전용
function InfoSection({ project, editable, onSaved, onError }) {
  const formId = useId();
  const toast = useToast();
  const initial = {
    name: project.name,
    description: project.description ?? "",
    startDate: project.start_date ?? "",
    endDate: project.end_date ?? "",
  };
  const [form, setForm] = useState(initial);
  const [serverErrors, setServerErrors] = useState({});
  const [saving, setSaving] = useState(false);

  if (!editable) {
    return (
      <Section title="프로젝트 정보">
        <dl className="grid gap-4 text-sm">
          <ReadOnlyItem label="이름" value={project.name} />
          <ReadOnlyItem label="설명" value={project.description || "—"} />
          <ReadOnlyItem
            label="기간"
            value={
              formatPeriod(project.start_date, project.end_date) || "기간 없음"
            }
          />
        </dl>
      </Section>
    );
  }

  const trimmedName = form.name.trim();
  const nameLength = countChars(trimmedName);
  const nameValid = nameLength >= 1 && nameLength <= NAME_MAX;
  // "YYYY-MM-DD" 문자열은 그대로 비교해도 날짜 순서와 같다
  const periodValid =
    !form.startDate || !form.endDate || form.endDate >= form.startDate;

  // 바뀐 필드만 보낸다(API-SPEC PATCH). 비운 설명·날짜는 null로 지운다.
  const patch = {};
  if (trimmedName !== project.name) patch.name = trimmedName;
  if (form.description.trim() !== initial.description)
    patch.description = form.description.trim() || null;
  if (form.startDate !== initial.startDate)
    patch.start_date = form.startDate || null;
  if (form.endDate !== initial.endDate) patch.end_date = form.endDate || null;
  const isDirty = Object.keys(patch).length > 0;

  // 이름은 처음부터 채워져 있으므로 틀린 순간 바로 보여 준다
  const nameError = nameValid ? serverErrors.name : NAME_ERROR;
  const endDateError = periodValid ? serverErrors.end_date : PERIOD_ERROR;

  // key = 폼 상태 이름, field = 서버 422 errors의 field 이름
  const set = (key, field) => (e) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
    setServerErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!isDirty || !nameValid || !periodValid || saving) return;
    setSaving(true);
    try {
      const updated = await updateProject(project.id, patch);
      // TODO(Figma): 저장 성공 토스트 문구는 시안 확정 전 추정값
      toast.success("프로젝트 정보를 저장했습니다");
      onSaved(updated); // key가 바뀌어 이 구역이 새로 그려진다
    } catch (error) {
      const fieldErrors = fieldErrorsOf(error);
      if (fieldErrors) setServerErrors(fieldErrors);
      else onError(error, "잠시 후 다시 시도해 주세요"); // 403 FORBIDDEN 등은 토스트
      setSaving(false);
    }
  };

  return (
    <Section title="프로젝트 정보">
      <form id={formId} onSubmit={submit} className="flex flex-col gap-4">
        <Input
          label="이름"
          required
          maxCount={NAME_MAX} // PRJ-01-b 남은 글자 수 n/30 — 수정도 같은 규칙
          value={form.name}
          onChange={set("name", "name")}
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
        <div className="flex justify-end">
          <Button
            type="submit"
            loading={saving}
            disabled={!isDirty || !nameValid || !periodValid}
          >
            저장
          </Button>
        </div>
      </form>
    </Section>
  );
}

function ReadOnlyItem({ label, value }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="font-semibold text-neutral-900">{label}</dt>
      <dd className="break-all whitespace-pre-line text-neutral-600">
        {value}
      </dd>
    </div>
  );
}

// 프로젝트 삭제 — 확인 창에서 프로젝트 이름을 똑같이 입력해야 `삭제`가 활성(PRJ-03, COMPONENTS §3.7)
function DeleteSection({ project, onError }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [opening, setOpening] = useState(false);
  const [taskCount, setTaskCount] = useState(null);
  const [typedName, setTypedName] = useState("");
  const [deleting, setDeleting] = useState(false);

  // 확인 창 문구의 "업무 n개" — 상태 필터 없이 1건만 받아 total만 읽는다.
  const openDialog = async () => {
    setOpening(true);
    try {
      const data = await listTasks(project.id, { size: 1 });
      setTaskCount(data.total);
    } catch {
      setTaskCount(null); // 개수를 몰라도 삭제는 할 수 있게 문구만 바꾼다
    }
    setTypedName("");
    setOpening(false);
    setOpen(true);
  };

  const close = () => {
    if (!deleting) setOpen(false);
  };

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await deleteProject(project.id);
      // TODO(Figma): 삭제 성공 토스트 문구는 시안 확정 전 추정값
      toast.success("프로젝트를 삭제했습니다");
      navigate("/projects", { replace: true }); // S7 → S3 (UI-DESIGN 화면 흐름)
    } catch (error) {
      setDeleting(false);
      setOpen(false);
      onError(error, "잠시 후 다시 시도해 주세요"); // 403 FORBIDDEN은 토스트, 404는 안내 화면
    }
  };

  const countText = taskCount == null ? "업무가" : `업무 ${taskCount}개가`;

  return (
    <Section title="프로젝트 삭제">
      <p className="mb-4 text-sm text-neutral-600">
        {/* SPEC §4 F2 규칙: 업무·댓글도 함께 사라지고 되돌릴 수 없다 */}
        삭제하면 업무·댓글이 함께 사라지고 되돌릴 수 없습니다
      </p>
      <Button variant="danger" onClick={openDialog} loading={opening}>
        프로젝트 삭제
      </Button>

      <ConfirmDialog
        open={open}
        title="프로젝트를 삭제하시겠습니까?"
        message={`${countText} 함께 삭제되고 되돌릴 수 없습니다.\n확인을 위해 프로젝트 이름(${project.name})을 입력해 주세요`}
        confirmLabel="삭제"
        danger
        loading={deleting}
        // 수용 기준(TASKS T-F2-06): 이름이 다르면 삭제 비활성. 앞뒤 공백도 다르게 본다.
        confirmDisabled={typedName !== project.name}
        onConfirm={confirmDelete}
        onCancel={close}
      >
        <Input
          aria-label="프로젝트 이름 확인"
          placeholder={project.name}
          autoFocus
          autoComplete="off"
          value={typedName}
          onChange={(e) => setTypedName(e.target.value)}
        />
      </ConfirmDialog>
    </Section>
  );
}
