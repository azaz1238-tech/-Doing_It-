import { useState } from "react";
import Avatar from "../../core/ui/Avatar";
import Button from "../../core/ui/Button";
import ConfirmDialog from "../../core/ui/ConfirmDialog";
import EmptyState from "../../core/ui/EmptyState";
import ErrorPage from "../../core/ui/ErrorPage";
import * as Icons from "../../core/ui/icons";
import Input from "../../core/ui/Input";
import Modal from "../../core/ui/Modal";
import { SkeletonList } from "../../core/ui/Skeleton";
import { useToast } from "../../core/ui/useToast";
import DueLabel from "../tasks/DueLabel";
import PriorityBadge from "../tasks/PriorityBadge";
import StatusSelect from "../tasks/StatusSelect";
import ProjectHeader from "../projects/ProjectHeader";

/**
 * 공통 컴포넌트 미리보기 — 개발 서버에서만 열린다(/dev/components, App.jsx).
 * 동잇 UI 시안 v0.3과 눈으로 비교하는 용도. 실제 화면이 아니며 API를 부르지 않는다.
 */

const COLORS = [
  ["primary", "bg-primary"],
  ["primary-hover", "bg-primary-hover"],
  ["primary-soft", "bg-primary-soft"],
  ["info", "bg-info"],
  ["success", "bg-success"],
  ["success-soft", "bg-success-soft"],
  ["warning", "bg-warning"],
  ["warning-soft", "bg-warning-soft"],
  ["danger", "bg-danger"],
  ["danger-soft", "bg-danger-soft"],
  ["danger-strong", "bg-danger-strong"],
  ["neutral-50", "bg-neutral-50"],
  ["neutral-100", "bg-neutral-100"],
  ["neutral-200", "bg-neutral-200"],
  ["neutral-300", "bg-neutral-300"],
  ["neutral-400", "bg-neutral-400"],
  ["neutral-500", "bg-neutral-500"],
  ["neutral-600", "bg-neutral-600"],
  ["neutral-700", "bg-neutral-700"],
  ["neutral-900", "bg-neutral-900"],
  ["avatar-1", "bg-avatar-1"],
  ["avatar-2", "bg-avatar-2"],
  ["avatar-3", "bg-avatar-3"],
  ["avatar-4", "bg-avatar-4"],
];

// DueLabel 예시는 오늘을 11/17로 고정한다(시안과 같은 날짜로 비교).
const DUE_TODAY = "2026-11-17";
const DUE_EXAMPLES = [
  ["2026-11-14", "지연"],
  ["2026-11-17", "오늘"],
  ["2026-11-18", "내일"],
  ["2026-11-20", "D-3"],
  ["2026-11-25", "그 이후"],
  [null, "없음"],
];

const USERS = [
  { id: 1, name: "이지수" },
  { id: 2, name: "김민호" },
  { id: 3, name: "박서연" },
  { id: 4, name: "최현우" },
];

// ProjectHeader 예시 — 멤버 6명이면 아바타 4개 + "+2"
const PREVIEW_PROJECT = {
  id: 1,
  name: "백엔드 MVP",
  start_date: "2026-11-10",
  end_date: "2026-11-19",
};
const PREVIEW_MEMBERS = [
  ...USERS,
  { id: 5, name: "정하늘" },
  { id: 6, name: "한도윤" },
].map((u) => ({ user_id: u.id, name: u.name }));

function Section({ title, children }) {
  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 className="mb-4 font-bold text-neutral-900">{title}</h2>
      {children}
    </section>
  );
}

export default function ComponentPreviewPage() {
  const toast = useToast();
  const [loginId, setLoginId] = useState("seoyeon01");
  const [password, setPassword] = useState("password1234");
  const [title, setTitle] = useState(
    "로그인 화면 오류 메시지 문구 정리하고 공통 컴포넌트로 빼기",
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [modalName, setModalName] = useState("");
  const [confirm, setConfirm] = useState(null);
  const [typedName, setTypedName] = useState("");
  const [status, setStatus] = useState("TODO");

  const closeModal = () => {
    setModalOpen(false);
    setModalName("");
  };

  const closeConfirm = () => {
    setConfirm(null);
    setTypedName("");
  };

  return (
    <div className="flex flex-col gap-6">
      <header>
        <p className="text-xs text-neutral-500">개발용 · 실제 화면 아님</p>
        <h1 className="text-2xl font-bold">공통 컴포넌트 미리보기</h1>
        <p className="mt-1 text-neutral-500">
          동잇 UI 시안 v0.3 · 쿨톤과 비교해 보세요. 목록은 docs/COMPONENTS.md
        </p>
      </header>

      <Section title="디자인 토큰 (index.css)">
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-6 lg:grid-cols-8">
          {COLORS.map(([name, bg]) => (
            <div key={name}>
              <div
                className={`h-12 rounded-lg border border-neutral-200 ${bg}`}
              />
              <p className="mt-1 text-xs text-neutral-600">{name}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="아이콘 (icons/index.jsx)">
        <div className="flex flex-wrap gap-4">
          {Object.entries(Icons).map(([name, Icon]) => (
            <div
              key={name}
              className="flex w-28 flex-col items-center gap-1 text-neutral-700"
            >
              <Icon size={20} />
              <span className="text-xs text-neutral-500">
                {name.replace("Icon", "")}
              </span>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Button">
        <div className="flex flex-wrap items-center gap-2">
          <Button>
            <Icons.PlusIcon />
            업무 추가
          </Button>
          <Button variant="secondary">취소</Button>
          <Button variant="ghost">초기화</Button>
          <Button variant="danger">삭제</Button>
          <Button disabled>만들기 (비활성)</Button>
          <Button loading>저장 중</Button>
          <Button size="sm">작은 버튼</Button>
        </div>
      </Section>

      <Section title="Input">
        <div className="grid max-w-md gap-4">
          <Input
            label="아이디"
            labelHint="영문 소문자·숫자 4~20자"
            error="이미 사용 중인 아이디입니다"
            value={loginId}
            onChange={(e) => setLoginId(e.target.value.toLowerCase())}
          />
          <Input
            label="비밀번호"
            labelHint="8~64자"
            type="password"
            success={password.length >= 8 ? "사용할 수 있습니다" : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Input
            label="제목"
            required
            maxCount={30}
            error={
              title.trim().length > 30
                ? "업무 제목은 1~30자로 입력해 주세요"
                : undefined
            }
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <Input label="비활성" disabled value="읽기 전용" readOnly />
        </div>
      </Section>

      <Section title="Avatar">
        <div className="flex items-center gap-3">
          {USERS.map((user) => (
            <Avatar key={user.id} user={user} />
          ))}
          <Avatar user={null} />
          <span className="text-neutral-500">← 담당자 없음</span>
          <div className="ml-6 flex -space-x-2">
            {USERS.map((user) => (
              <Avatar
                key={user.id}
                user={user}
                size="sm"
                className="ring-2 ring-white"
              />
            ))}
          </div>
        </div>
      </Section>

      <Section title="ProjectHeader (features/projects · S4·S7)">
        <div className="grid gap-8">
          <ProjectHeader
            project={PREVIEW_PROJECT}
            members={PREVIEW_MEMBERS}
            active="board"
            actions={
              <Button>
                <Icons.PlusIcon />
                업무 추가
              </Button>
            }
          />
          <ProjectHeader
            project={{ ...PREVIEW_PROJECT, start_date: null, end_date: null }}
            members={PREVIEW_MEMBERS.slice(0, 2)}
            active="settings"
          />
          <ProjectHeader project={null} active="board" />
        </div>
      </Section>

      <Section title="업무용 배지 (features/tasks · T-F0-13)">
        <div className="grid gap-5">
          <div className="flex flex-wrap items-center gap-2">
            {["URGENT", "HIGH", "MEDIUM", "LOW"].map((p) => (
              <PriorityBadge key={p} priority={p} />
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusSelect value={status} onChange={setStatus} />
            <StatusSelect value="IN_PROGRESS" disabled />
            <StatusSelect value="DONE" readOnly />
            <span className="text-neutral-500">
              ← 변경 가능 · 요청 중 · 권한 없음(🔒)
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {DUE_EXAMPLES.map(([due, desc]) => (
              <div key={desc} className="flex flex-col items-start gap-1">
                <DueLabel dueDate={due} status="TODO" today={DUE_TODAY} />
                <span className="text-xs text-neutral-400">{desc}</span>
              </div>
            ))}
            <span className="text-neutral-500">
              (오늘 = 11/17 고정 · 완료 업무는 표시 안 함)
            </span>
          </div>
        </div>
      </Section>

      <Section title="Toast (화면 아래 가운데, 3초)">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => toast.success("상태를 '진행 중'으로 변경했습니다")}
          >
            성공
          </Button>
          <Button
            variant="secondary"
            onClick={() => toast.error("상태를 바꿀 권한이 없습니다")}
          >
            오류
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              toast.warning("로그인이 만료되었습니다. 다시 로그인해 주세요")
            }
          >
            세션 만료
          </Button>
        </div>
      </Section>

      <Section title="Modal · ConfirmDialog">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setModalOpen(true)}>
            새 프로젝트 모달
          </Button>
          <Button variant="secondary" onClick={() => setConfirm("task")}>
            업무 삭제 (S6)
          </Button>
          <Button variant="secondary" onClick={() => setConfirm("member")}>
            멤버 제거 (S7)
          </Button>
          <Button variant="secondary" onClick={() => setConfirm("project")}>
            프로젝트 삭제 (S7)
          </Button>
        </div>

        <Modal
          open={modalOpen}
          onClose={closeModal}
          title="새 프로젝트"
          subtitle="만든 사람이 OWNER가 됩니다"
          isDirty={modalName !== ""}
          footer={
            <>
              <Button variant="secondary" onClick={closeModal}>
                취소
              </Button>
              <Button disabled={modalName.trim() === ""}>만들기</Button>
            </>
          }
        >
          <Input
            label="이름"
            required
            maxCount={30}
            value={modalName}
            onChange={(e) => setModalName(e.target.value)}
          />
        </Modal>

        <ConfirmDialog
          open={confirm === "task"}
          title="이 업무를 삭제하시겠습니까?"
          message={
            "'업무 상태 변경 API' 업무가 삭제됩니다.\n변경 이력은 남습니다"
          }
          confirmLabel="삭제"
          danger
          onConfirm={closeConfirm}
          onCancel={closeConfirm}
        />
        <ConfirmDialog
          open={confirm === "member"}
          title="김민호님을 멤버에서 제거하시겠습니까?"
          message={
            <>
              김민호님이 담당하던 업무는{" "}
              <strong className="font-semibold text-neutral-900">
                담당자 없음
              </strong>
              이 됩니다
            </>
          }
          confirmLabel="제거"
          danger
          onConfirm={closeConfirm}
          onCancel={closeConfirm}
        />
        <ConfirmDialog
          open={confirm === "project"}
          title="프로젝트를 삭제하시겠습니까?"
          message={
            "업무 12개가 함께 삭제되고 되돌릴 수 없습니다.\n확인을 위해 프로젝트 이름(백엔드 MVP)을 입력해 주세요"
          }
          confirmLabel="삭제"
          danger
          confirmDisabled={typedName !== "백엔드 MVP"}
          onConfirm={closeConfirm}
          onCancel={closeConfirm}
        >
          <Input
            aria-label="프로젝트 이름"
            placeholder="백엔드 MVP"
            value={typedName}
            onChange={(e) => setTypedName(e.target.value)}
          />
        </ConfirmDialog>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="ErrorPage · 403 (S8)">
          <ErrorPage type="403" />
        </Section>
        <Section title="ErrorPage · 404 (S8)">
          <ErrorPage type="404" />
        </Section>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Section title="빈 상태 · 프로젝트 0개 (S3)">
          <EmptyState
            icon={Icons.FolderIcon}
            title="프로젝트가 없습니다"
            description="프로젝트를 만들어 보세요"
            action={
              <Button>
                <Icons.PlusIcon />첫 프로젝트 만들기
              </Button>
            }
          />
        </Section>
        <Section title="빈 상태 · 컬럼 (S4)">
          <div className="rounded-lg bg-neutral-100 p-4">
            <p className="mb-3 flex items-center gap-2 font-semibold">
              <span className="size-2 rounded-full bg-primary" />
              진행 중 <span className="text-neutral-400">0</span>
            </p>
            <EmptyState
              variant="column"
              title="진행 중인 업무가 없습니다"
              description="카드의 상태를 바꾸면 여기로 옮겨집니다"
            />
          </div>
        </Section>
        <Section title="불러오는 중 · 스켈레톤">
          <SkeletonList />
        </Section>
      </div>
    </div>
  );
}
