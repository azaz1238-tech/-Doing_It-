import { useCallback, useEffect, useId, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useAuth } from "../../core/auth/useAuth";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import ConfirmDialog from "../../core/ui/ConfirmDialog";
import ErrorPage from "../../core/ui/ErrorPage";
import Input from "../../core/ui/Input";
import Skeleton from "../../core/ui/Skeleton";
import { cn } from "../../core/utils/cn";
import { useToast } from "../../core/ui/useToast";
import { formatPeriod } from "../../core/utils/date";
import { listTasks } from "../tasks/api";
import {
  addMember,
  deleteProject,
  getProject,
  listMembers,
  removeMember,
  updateProject,
} from "./api";
import ProjectHeader from "./ProjectHeader";
import {
  countChars,
  DESCRIPTION_ERROR,
  NAME_ERROR,
  NAME_MAX,
  PERIOD_ERROR,
  ROLE_STYLES,
} from "./projectRules";

// S7 프로젝트 설정 — UI-DESIGN §4 S7 · PRJ-03(수정·삭제) · PRJ-04·05·07(멤버) · US-07·08·09
// 한 페이지에 세 구역(프로젝트 정보 · 멤버 · 프로젝트 삭제). 하위 주소나 탭은 만들지 않는다.
// 버튼 숨김은 편의 기능이다. 권한 판단은 백엔드가 한다(MEMBER가 다른 방법으로 시도하면 403).

// 페이지 진입 오류 → S8 안내 화면. 버튼 동작 중 403 FORBIDDEN은 토스트만 띄운다.
// 404는 code로 가른다 — USER_NOT_FOUND·MEMBER_NOT_FOUND도 404라서 상태 코드만 보면 안 된다.
function pageErrorOf(error) {
  const code = error.response?.data?.code;
  if (code === "NOT_PROJECT_MEMBER") return "403";
  if (code === "PROJECT_NOT_FOUND") return "404";
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
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [members, setMembers] = useState(null);
  const [pageError, setPageError] = useState(null); // "403" | "404" | null
  // 403·404가 아닌 실패(500·서버 꺼짐·네트워크)는 안내 화면 대신 "다시 시도"를 보인다(D9-04).
  const [projectFailed, setProjectFailed] = useState(false);
  const [membersFailed, setMembersFailed] = useState(false);
  const [attempt, setAttempt] = useState(0); // 다시 시도하면 1 늘려 effect를 다시 돌린다

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
        if (kind) {
          setPageError(kind);
          return;
        }
        setProjectFailed(true);
        toast.error(
          error.response?.data?.message ?? "프로젝트를 불러오지 못했습니다",
        );
      });
    return () => {
      ignore = true;
    };
  }, [projectId, toast, attempt]);

  // 멤버 목록 — 헤더 아바타와 멤버 구역이 같이 쓴다. 추가·제거 뒤 다시 부른다(T-F3-05 "목록 갱신").
  // 실패하면 이전 목록은 그대로 두고 실패만 표시한다(권한·없음 안내는 getProject 쪽이 맡는다).
  // OWNER가 항상 1명 이상이라 정상 응답이 0명일 수는 없다 → 빈 목록과 실패를 따로 구분한다.
  const loadMembers = useCallback(
    () =>
      listMembers(projectId)
        .then((data) => {
          setMembers(data.items);
          setMembersFailed(false);
        })
        .catch(() => setMembersFailed(true)),
    [projectId],
  );

  const retryProject = () => {
    setProjectFailed(false);
    setAttempt((n) => n + 1);
    if (membersFailed) {
      setMembersFailed(false);
      loadMembers();
    }
  };

  const retryMembers = () => {
    setMembersFailed(false);
    loadMembers();
  };

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  // S8 안내 화면. PRJ-07-a: 비멤버에게는 프로젝트 이름도 보이지 않는다(헤더를 그리지 않음).
  if (pageError === "403") return <ErrorPage type="403" />;
  if (pageError === "404")
    return <ErrorPage type="404" title="프로젝트를 찾을 수 없습니다" />;

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
          <MemberSection
            projectId={project.id}
            members={members}
            loadFailed={membersFailed}
            onRetry={retryMembers}
            editable={isOwner}
            myId={user?.id}
            onChanged={loadMembers}
            onError={handleError}
          />
          {/* MEMBER에게는 삭제 구역을 숨긴다(UI-DESIGN S7) */}
          {isOwner && <DeleteSection project={project} onError={handleError} />}
        </>
      ) : projectFailed ? (
        <LoadFailed
          message="프로젝트를 불러오지 못했습니다"
          onRetry={retryProject}
        />
      ) : (
        <div aria-hidden="true" className="flex flex-col gap-3">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-40 w-full max-w-xl" />
        </div>
      )}
    </div>
  );
}

// 불러오기 실패 + 다시 시도 (S3 목록 실패와 같은 모양)
function LoadFailed({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 text-sm text-neutral-500">
      <p>{message}</p>
      <Button variant="secondary" onClick={onRetry}>
        다시 시도
      </Button>
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
  // 빠르게 두 번 누르면 saving이 바뀌기 전에 두 번째 요청이 나간다 → ref로 바로 막는다(#56과 같은 방식).
  const savingRef = useRef(false);

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
  const trimmedDesc = form.description.trim();
  const descValid = trimmedDesc !== "";
  // "YYYY-MM-DD" 문자열은 그대로 비교해도 날짜 순서와 같다
  const periodValid =
    !form.startDate || !form.endDate || form.endDate >= form.startDate;

  // 바뀐 필드만 보낸다(API-SPEC PATCH). 비운 날짜는 null로 지운다. 설명은 비울 수 없다.
  const patch = {};
  if (trimmedName !== project.name) patch.name = trimmedName;
  if (trimmedDesc !== initial.description) patch.description = trimmedDesc;
  if (form.startDate !== initial.startDate)
    patch.start_date = form.startDate || null;
  if (form.endDate !== initial.endDate) patch.end_date = form.endDate || null;
  const isDirty = Object.keys(patch).length > 0;

  // 이름은 처음부터 채워져 있으므로 틀린 순간 바로 보여 준다
  const nameError = nameValid ? serverErrors.name : NAME_ERROR;
  const descError = descValid ? serverErrors.description : DESCRIPTION_ERROR;
  const endDateError = periodValid ? serverErrors.end_date : PERIOD_ERROR;

  // key = 폼 상태 이름, field = 서버 422 errors의 field 이름
  const set = (key, field) => (e) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
    setServerErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!isDirty || !nameValid || !descValid || !periodValid) return;
    if (savingRef.current) return;
    savingRef.current = true;
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
      savingRef.current = false;
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
            <span className="ml-0.5 text-danger">*</span>
          </label>
          <textarea
            id={`${formId}-desc`}
            rows={3}
            required
            value={form.description}
            onChange={set("description", "description")}
            placeholder="어떤 목표의 프로젝트인지 적어 주세요 (필수)"
            aria-invalid={descError ? true : undefined}
            aria-describedby={descError ? `${formId}-desc-error` : undefined}
            className={cn(
              "w-full resize-y rounded-lg border bg-white px-3 py-2 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-2 focus:-outline-offset-1",
              descError
                ? "border-danger focus:outline-danger"
                : "border-neutral-300 focus:outline-primary",
            )}
          />
          {descError && (
            <p id={`${formId}-desc-error`} className="text-xs text-danger">
              {descError}
            </p>
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
            disabled={!isDirty || !nameValid || !descValid || !periodValid}
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
  const deletingRef = useRef(false); // 두 번 클릭 방지

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
    if (deletingRef.current) return;
    deletingRef.current = true;
    setDeleting(true);
    try {
      await deleteProject(project.id);
      // TODO(Figma): 삭제 성공 토스트 문구는 시안 확정 전 추정값
      toast.success("프로젝트를 삭제했습니다");
      navigate("/projects", { replace: true }); // S7 → S3 (UI-DESIGN 화면 흐름)
    } catch (error) {
      deletingRef.current = false;
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

// 멤버 구역 문구 — SPEC 따옴표 문구 = 백엔드 member_service 문구
// (409 문구는 SPEC PRJ-04-c — UI-DESIGN S7도 v1.9에서 같은 문구로 맞춤, #75)
const ADD_ERRORS = {
  USER_NOT_FOUND: "해당 아이디의 회원이 없습니다", // PRJ-04-b
  ALREADY_MEMBER: "이미 프로젝트 멤버입니다", // PRJ-04-c
};
const LAST_OWNER_ERROR = "OWNER는 최소 1명 있어야 합니다"; // PRJ-05-b

const SELECT_CLASS =
  "h-10 rounded-lg border border-neutral-300 bg-white px-3 text-sm text-neutral-900 focus:outline-2 focus:-outline-offset-1 focus:outline-primary";

// 멤버 — 모든 멤버가 목록(이름·아이디·역할)을 본다(PRJ-07-b).
// OWNER만 아이디 + 역할로 추가(PRJ-04), 행마다 제거(PRJ-05).
function MemberSection({
  projectId,
  members,
  loadFailed,
  onRetry,
  editable,
  myId,
  onChanged,
  onError,
}) {
  const navigate = useNavigate();
  const toast = useToast();
  const formId = useId();
  const [loginId, setLoginId] = useState("");
  const [role, setRole] = useState("MEMBER");
  const [addError, setAddError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [target, setTarget] = useState(null); // 제거 확인 창에 띄운 Member
  const [removing, setRemoving] = useState(false);
  // 두 번 클릭 방지 — 상태보다 먼저 바뀌는 ref로 막는다
  const addingRef = useRef(false);
  const removingRef = useRef(false);

  const submitAdd = async (e) => {
    e.preventDefault();
    const value = loginId.trim();
    if (!value || addingRef.current) return;
    addingRef.current = true;
    setAdding(true);
    try {
      const member = await addMember(projectId, { loginId: value, role });
      // TODO(Figma): 멤버 추가 성공 토스트 문구는 시안 확정 전 추정값
      toast.success(`${member.name}님을 멤버로 추가했습니다`);
      setLoginId("");
      setRole("MEMBER");
      await onChanged();
    } catch (error) {
      const code = error.response?.data?.code;
      const fieldError = fieldErrorsOf(error)?.login_id;
      // PRJ-04-b·c: 입력 필드 아래에 보여 준다(UI-DESIGN S7). 403 FORBIDDEN 등은 토스트
      if (ADD_ERRORS[code]) setAddError(ADD_ERRORS[code]);
      else if (fieldError) setAddError(fieldError);
      else onError(error, "잠시 후 다시 시도해 주세요");
    }
    addingRef.current = false;
    setAdding(false);
  };

  const confirmRemove = async () => {
    if (removingRef.current) return;
    removingRef.current = true;
    const removed = target;
    setRemoving(true);
    try {
      await removeMember(projectId, removed.user_id);
      // TODO(Figma): 멤버 제거 성공 토스트 문구는 시안 확정 전 추정값
      toast.success(`${removed.name}님을 멤버에서 제거했습니다`);
      // 나를 제거했으면(OWNER가 2명 이상일 때) 이 프로젝트를 더 볼 수 없다 → 목록으로
      if (removed.user_id === myId) {
        navigate("/projects", { replace: true });
        return;
      }
      setTarget(null);
      await onChanged();
    } catch (error) {
      const code = error.response?.data?.code;
      setTarget(null);
      if (code === "LAST_OWNER") toast.error(LAST_OWNER_ERROR);
      else {
        onError(error, "잠시 후 다시 시도해 주세요");
        // 그 사이 다른 OWNER가 먼저 제거했으면(MEMBER_NOT_FOUND) 목록을 다시 맞춘다
        if (code === "MEMBER_NOT_FOUND") onChanged();
      }
    }
    removingRef.current = false;
    setRemoving(false);
  };

  return (
    <Section title="멤버">
      {editable && (
        <form
          id={formId}
          onSubmit={submitAdd}
          className="mb-5 flex flex-wrap items-start gap-2"
        >
          <Input
            label="아이디"
            className="min-w-48 flex-1"
            placeholder="추가할 회원의 아이디"
            autoComplete="off"
            value={loginId}
            onChange={(e) => {
              setLoginId(e.target.value);
              setAddError(null);
            }}
            error={addError}
          />
          <div className="flex flex-col gap-1.5">
            <label
              htmlFor={`${formId}-role`}
              className="font-semibold text-neutral-900"
            >
              역할
            </label>
            <select
              id={`${formId}-role`}
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className={SELECT_CLASS}
            >
              <option value="MEMBER">MEMBER</option>
              <option value="OWNER">OWNER</option>
            </select>
          </div>
          {/* 라벨 줄 높이만큼 내려 입력칸과 버튼 줄을 맞춘다 */}
          <Button
            type="submit"
            className="mt-7"
            loading={adding}
            disabled={!loginId.trim()}
          >
            추가
          </Button>
        </form>
      )}

      {/* 처음 불러오기 실패 → 다시 시도. 목록이 있는데 새로고침이 실패하면 이전 목록 위에 알림만 */}
      {loadFailed && members != null && (
        <p className="mb-3 flex flex-wrap items-center gap-2 text-sm text-neutral-500">
          멤버 목록을 새로 불러오지 못했습니다
          <Button variant="ghost" size="sm" onClick={onRetry}>
            다시 시도
          </Button>
        </p>
      )}
      {members == null && loadFailed ? (
        <LoadFailed
          message="멤버 목록을 불러오지 못했습니다"
          onRetry={onRetry}
        />
      ) : members == null ? (
        <div aria-hidden="true" className="flex flex-col gap-3">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : (
        <ul className="divide-y divide-neutral-200">
          {members.map((m) => (
            <li key={m.user_id} className="flex items-center gap-3 py-3">
              <Avatar user={{ id: m.user_id, name: m.name }} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-neutral-900">
                  {m.name}
                </p>
                <p className="truncate text-xs text-neutral-500">
                  {m.login_id}
                </p>
              </div>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-semibold",
                  ROLE_STYLES[m.role],
                )}
              >
                {m.role}
              </span>
              {editable && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setTarget(m)}
                  aria-label={`${m.name}님 제거`}
                >
                  제거
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={target != null}
        title={target ? `${target.name}님을 멤버에서 제거하시겠습니까?` : ""}
        message={
          target && (
            // COMPONENTS §3.7 · UI-DESIGN S7 (PRJ-05)
            <>
              {target.name}님이 담당하던 업무는{" "}
              <strong className="text-neutral-900">담당자 없음</strong>이 됩니다
            </>
          )
        }
        confirmLabel="제거"
        danger
        loading={removing}
        onConfirm={confirmRemove}
        onCancel={() => !removing && setTarget(null)}
      />
    </Section>
  );
}
