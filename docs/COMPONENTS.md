# 공통 컴포넌트 목록 (COMPONENTS.md)

> 프로젝트: 동잇(Doing_It) | 작성: 최진영(FE-A) | 작성일: 2026-11-16 (5일차 산출물) | 태스크: T-F0-12
> 근거: UI-DESIGN §3(공통 레이아웃) · §5(공통 컴포넌트) · §6(표시 규칙) · §8(Figma와 MVP 차이), ARCHITECTURE §5, **동잇 UI 시안 v0.3 · 쿨톤** (김서현 작성, D4-05)
> 컴포넌트를 추가·변경하면 이 표도 같은 PR에서 고친다.

## 1. 한눈에 보기

| 컴포넌트 | 위치 | 담당 | 상태 | P0 사용처 |
| --- | --- | --- | --- | --- |
| 디자인 토큰 | `src/index.css` | 최진영 | 완료 (시안 v0.3 값) | 전체 |
| Icon | `core/ui/icons/index.jsx` | 최진영 | 완료 | 전체 |
| Button | `core/ui/Button.jsx` | 최진영 | 완료 | 전체 |
| Input | `core/ui/Input.jsx` | 최진영 | 완료 | S1, S2, S3, S5, S7 |
| Avatar | `core/ui/Avatar.jsx` | 최진영 | 완료 | TopBar, 카드, 멤버 |
| Modal | `core/ui/Modal.jsx` | 최진영 | 완료 | S3, S5, S6, S7 |
| ConfirmDialog | `core/ui/ConfirmDialog.jsx` | 최진영 | 완료 | S6, S7 |
| Toast | `core/ui/ToastProvider.jsx`, `core/ui/useToast.js` | 최진영 | 완료 | 전체 |
| TopBar | `core/layout/TopBar.jsx` | 최진영 | 완료 | S3~S8 |
| AppLayout | `core/layout/AppLayout.jsx` | 최진영 | 완료 | S3~S8 (라우터) |
| ProtectedRoute | `core/auth/ProtectedRoute.jsx` | 최진영 | 완료 (T-F0-11, 로그인 화면 연결은 T-F1-05 · 11/17) | 라우터 |
| EmptyState | `core/ui/EmptyState.jsx` | 최진영 | 완료 | S3, S4 |
| Skeleton | `core/ui/Skeleton.jsx` | 최진영 | 완료 | S3, S4, S6 |
| 날짜 유틸 | `core/utils/date.js` | 김서현·최진영 | 완료 (T-F0-13 DueLabel용, T-F2-05 `formatPeriod` 기간 표시) | 카드, 상세, S3 카드, S4 헤더 |
| ErrorPage (403·404) | `core/ui/ErrorPage.jsx` | 김서현 | 완료 (T-F0-14) | S8 |
| PriorityBadge | `features/tasks/PriorityBadge.jsx` | 김서현 | 완료 (T-F0-13) | 카드, 상세 |
| StatusSelect | `features/tasks/StatusSelect.jsx` | 김서현 | 완료 (T-F0-13) | 카드, 상세 |
| DueLabel | `features/tasks/DueLabel.jsx` | 김서현 | 완료 (T-F0-13) | 카드, 상세 |
| ProjectHeader | `features/projects/ProjectHeader.jsx` | 최진영 | 완료 (11/18, S4·S7 연결 전) | S4, S7 |
| MemberSelect | `features/projects/MemberSelect.jsx` | 김서현 | 완료 (T-F2-12에서 기본형) | S5, S6 |
| TaskCard | `features/tasks/TaskCard.jsx` | 김서현 | 완료 (T-F2-10, 목 데이터) | S4 |
| TaskFormModal | `features/tasks/TaskFormModal.jsx` | 김서현 | 완료 (T-F2-12, API 연결 T-F2-11) | S5 |
| TaskDetailModal | `features/tasks/TaskDetailModal.jsx` | 김서현 | 완료 (T-F2-13) | S6 |

- **상태 뜻:** 완료 = 코드가 있고 린트·빌드 통과 / 미착수 = 코드 없음.
- **ErrorPage 담당:** TASKS.md(11/16 조 편성)대로 김서현이 맡는다(11/16 확인).
- **ProjectHeader·MemberSelect** 담당은 11/17 FE 두 명이 정했다: ProjectHeader는 최진영(S7과 이어짐), MemberSelect는 김서현(S5·S6에서 씀). 둘 다 데이터를 props로 받아 그리기만 하고, S4는 프로젝트·멤버를 한 번 받아 둘에 넘긴다.
- 폴더는 ARCHITECTURE §5.1의 `features/projects`·`features/tasks`(복수형). 업무용 배지는 동잇 고유 값을 다루므로 `features/tasks`에 둔다(UI-DESIGN v1.1 §5, SPEC-CHANGELOG #9).

## 2. 사용 규칙

- `core/`는 `features/`를 import하지 않는다(스타터킷 재사용). 화면 전용 컴포넌트는 `features/`에 둔다.
- 아이콘·클래스 병합·상태관리 라이브러리를 추가하지 않는다. 아이콘은 lucide SVG(ISC)를 복사해 `icons/index.jsx`에 추가하고, 클래스 병합은 `core/utils/cn.js`를 쓴다.
- 색은 **§3.1 토큰 클래스만** 쓴다. `bg-rose-500`처럼 Tailwind 기본 색을 직접 쓰지 않는다. `neutral-800`은 팔레트에 없으므로 쓰지 않는다.
- 문구는 `~합니다`체(UI-DESIGN §6.5, 11/16 회의). SPEC 따옴표 문구는 글자 그대로 쓰고, 질문은 `~하시겠습니까?`, 문장 끝 마침표는 붙이지 않는다. 화면에 나올 오류는 `code`로 SPEC 문구를 고르고, 모르는 `code`만 서버 `message`를 보여 준다. 서버 `message`는 텍스트로만 넣는다(`dangerouslySetInnerHTML` 금지).
- 버튼 숨김·비활성은 편의 기능이다. 권한 판단은 백엔드가 한다.
- **미리보기:** `npm run dev` 후 `http://localhost:5173/dev/components`에서 모든 공통 컴포넌트를 한 화면에서 본다(`features/dev/ComponentPreviewPage.jsx`, 개발 서버에서만 열리고 배포 빌드에는 빠진다). 컴포넌트를 추가하면 여기에도 예시를 넣는다.
- 시안·Figma 확정 전 추정값에는 `TODO(UI-DESIGN §7 확정 전)` 또는 `TODO(Figma)`를 단다. 남은 항목은 `grep -rn "TODO(" src`로 찾는다.

## 3. 컴포넌트 상세

### 3.1 디자인 토큰 — `src/index.css`

시안 v0.3 · 쿨톤 팔레트. 의미 구분(빨강=긴급·지연, 주황=높음·임박, 파랑=보통·진행 중, 초록=완료)은 UI-DESIGN §6 그대로이고 채도만 낮췄다.

| 토큰 | Tailwind 클래스 예 | 용도 | 값 |
| --- | --- | --- | --- |
| `primary` | `bg-primary`, `text-primary` | 주 버튼, 선택, 진행 중 | `#4467A8` |
| `primary-hover` | `hover:bg-primary-hover` | 버튼 누를 때 | `#375792` |
| `primary-soft` | `bg-primary-soft` | 진행 중 칩 배경 | `#EBF0F8` |
| `info` | `text-info` | 보통 | `#5E86C1` |
| `success` / `success-soft` | `text-success`, `bg-success-soft` | 완료 / 완료 칩 배경 | `#3E9C8F` / `#E5F3F1` |
| `warning` / `warning-soft` | `text-warning`, `bg-warning-soft` | 높음·임박 / 임박 배지 배경 | `#B07A2A` / `#F7F0E3` |
| `danger` / `danger-soft` | `bg-danger`, `bg-danger-soft` | 긴급·지연·삭제 / 지연 배지·폼 오류 상자 | `#B94A63` / `#FAEDF0` |
| `danger-strong` | `bg-danger-strong` | 오류 토스트 배경 | `#6B2E3D` (v0.3 시안 원본, 김서현 11/16 확인) |
| `neutral-50` | `bg-neutral-50` | 배경 | `#F5F7FA` |
| `neutral-100` | `bg-neutral-100` | 칸반 컬럼 | `#EEF1F5` |
| `neutral-200` | `border-neutral-200` | 테두리, 스켈레톤 막대 | `#E2E7EE` |
| `neutral-300` | `border-neutral-300` | 입력 테두리 | `#CDD5DF` |
| `neutral-400` | `text-neutral-400` | 흐린 글자 | `#9AA5B4` |
| `neutral-500` | `text-neutral-500` | 보조 글자 | `#6B7889` |
| `neutral-600` | `text-neutral-600` | 본문 보조 | `#4D596A` |
| `neutral-700` | `text-neutral-700` | 버튼 글자 | `#364152` |
| `neutral-900` | `text-neutral-900` | 제목·본문 | `#1C2433` |
| `avatar-1~4` | `bg-avatar-1` | 아바타 | `#7084C9` · `#4F97B5` · `#4A9D90` · `#8C7CC4` |
| `--font-sans` | 기본 | 글꼴 | 시스템 글꼴 (미정) |

- 카드는 `bg-white`(n0). 기본 글자 14px(`body`).
- 모서리: 카드·입력 8px(`rounded-lg`), 모달 12px(`rounded-xl`), 배지 4px(`rounded`).
- ⚠ UI-DESIGN §7 표는 아직 v0.2(원색) 값이다. 시안 메모대로 **문서 → Figma → 코드** 순서로 §7을 먼저 고쳐야 한다(문서 주인: 양준석).

### 3.2 Icon — `core/ui/icons/index.jsx`

| 이름 | 쓰임 |
| --- | --- |
| `ChevronDownIcon` | TopBar 메뉴 ▾, 드롭다운 |
| `LogOutIcon` | 로그아웃, 세션 만료 토스트 |
| `XIcon` | 모달 닫기 |
| `PlusIcon` | `+ 새 프로젝트`, `+ 업무 추가` |
| `CheckIcon` | 성공 토스트, 입력 성공 문구, 선택 표시 |
| `ClockIcon` | DueLabel "오늘 마감"·"D-n" |
| `TriangleAlertIcon` | DueLabel "n일 지남", 오류 토스트, 로그인 실패 상자 |
| `InfoIcon` | 안내 문구 (예: "OWNER는 최소 1명 있어야 합니다") |
| `LockIcon` | 권한 없는 상태·항목 🔒 |
| `FolderIcon` | 프로젝트 카드, S3 빈 상태 |
| `CalendarIcon` | 기간·날짜 입력 |
| `EyeIcon` / `EyeOffIcon` | 비밀번호 보기·숨기기 |
| `LoaderIcon` | Button 로딩 (회전) |
| `ShieldAlertIcon` / `CompassIcon` | S8 ErrorPage 403 / 404 (시안 방패·나침반, T-F0-14) |

공통 props: `size`(기본 16), `className`(색은 `text-*`로 지정). 화면 읽기 프로그램에서는 숨겨진다(`aria-hidden`).

```jsx
<ClockIcon className="text-warning" />
```

### 3.3 Button — `core/ui/Button.jsx`

| prop | 값 | 기본 | 설명 |
| --- | --- | --- | --- |
| `variant` | `primary` · `secondary` · `ghost` · `danger` | `primary` | 시안: `+ 업무 추가` · `취소` · `초기화` · `삭제` |
| `size` | `sm` · `md` | `md` | |
| `loading` | boolean | `false` | 요청 중이면 스피너 + 비활성 → 두 번 제출 방지 |
| `type` | `button` · `submit` | `button` | 폼 제출 버튼은 `type="submit"` |
| 그 외 | `onClick`, `disabled`, `className` … | | `<button>`에 그대로 전달 |

```jsx
<Button type="submit" loading={submitting}>가입하기</Button>
<Button variant="danger" onClick={openDelete}>삭제</Button>
```

- 시안의 "만들기"·"업무 추가" 흐린 버튼은 `disabled` 상태다(입력 오류가 있을 때).

### 3.4 Input — `core/ui/Input.jsx`

| prop | 설명 |
| --- | --- |
| `label` | 라벨 문구 |
| `labelHint` | 라벨 옆 흐린 안내 (시안 S2: `아이디 · 영문 소문자·숫자 4~20자`) |
| `required` | 라벨 옆 `*` 표시 |
| `error` | 오류 문구. 있으면 빨간 테두리 + `aria-invalid` |
| `success` | 성공 문구, 앞에 ✓ (예: `사용할 수 있습니다`). `error`가 있으면 숨김 |
| `hint` | 오류·성공 문구가 없을 때 보이는 도움말 |
| `maxCount` | 오른쪽에 글자 수 `6/30` 표시, 넘으면 빨간색. 입력을 막지는 않는다(시안 S5의 `34/30`처럼 넘친 상태를 보여 줌) |
| `type="password"` | 오른쪽에 보기·숨기기 버튼(👁)이 붙는다 |
| 그 외 | `value`, `onChange`, `ref` … `<input>`에 그대로 전달 |

```jsx
// S2 회원가입
<Input
  label="아이디"
  labelHint="영문 소문자·숫자 4~20자"
  error={errors.login_id}
  value={form.loginId}
  onChange={(e) => setForm({ ...form, loginId: e.target.value.toLowerCase() })}
/>
<Input label="비밀번호" labelHint="8~64자" type="password" … />
<Input label="이름" … />  {/* 사용자 이름 1~50자 — 글자 수 표시 없음 */}

// S3 새 프로젝트 · S7 설정 — 프로젝트 이름 1~30자
<Input label="이름" required maxCount={30} value={name} onChange={…} />
```

### 3.5 Avatar — `core/ui/Avatar.jsx`

| prop | 설명 |
| --- | --- |
| `user` | `{ id, name }` (UserBrief). `null`이면 담당자 없음 → 회색 `?` |
| `size` | `sm`(24px) · `md`(32px, 기본) |

- 색은 `user.id`로 정해져 같은 사용자는 어디서나 같은 색이다. `avatar-1~4` 토큰 4색을 돌려 쓴다.
- 글자는 시안 v0.3처럼 이름 첫 글자다. 한글 3자 이름은 성을 뺀 둘째 글자(김민호 → 민), 그 밖(2자·4자·영문)은 첫 글자. (김서현 확인 필요)

```jsx
<Avatar user={task.assignee} size="sm" />
```

### 3.6 Modal — `core/ui/Modal.jsx`

| prop | 설명 |
| --- | --- |
| `open` | 열림 여부 |
| `onClose` | 닫기 요청 시 호출 |
| `title` | 머리글 제목 |
| `subtitle` | 제목 아래 흐린 부제 (시안 S3 `만든 사람이 OWNER가 됩니다`, S5 `'할 일' 칸에 추가됩니다`) |
| `footer` | 아래 버튼 영역 |
| `isDirty` | 입력 중이면 `true` → ESC·바깥 클릭·✕ 때 "작성 중인 내용이 사라집니다. 닫으시겠습니까?" 확인 |
| `showClose` | 오른쪽 위 ✕ 표시 (기본 `true`). ConfirmDialog는 `false` |
| `size` | `sm` · `md`(기본) · `lg` |

- 시안 v0.3처럼 제목·본문·버튼 사이에 구분선이 없다. ESC·바깥 클릭·✕로 닫는다. 열리면 포커스가 모달로 가고, 닫히면 원래 자리로 돌아간다. 배경 스크롤을 막는다. 배경은 `neutral-900` 40%.
- 모달 위에 ConfirmDialog가 뜨면 ESC는 맨 위 모달만 닫는다.

```jsx
<Modal
  open={open}
  onClose={() => setOpen(false)}
  title="새 프로젝트"
  subtitle="만든 사람이 OWNER가 됩니다"
  isDirty={name !== ""}
  footer={<Button type="submit" form="project-form">만들기</Button>}
>
  <form id="project-form" onSubmit={handleSubmit}>…</form>
</Modal>
```

### 3.7 ConfirmDialog — `core/ui/ConfirmDialog.jsx`

| prop | 설명 |
| --- | --- |
| `open`, `title`, `message` | |
| `confirmLabel` / `cancelLabel` | 기본 `확인` / `취소` |
| `danger` | 확인 버튼을 빨간색으로 |
| `loading` | 요청 중 버튼 비활성 |
| `confirmDisabled` | 예: S7 프로젝트 이름이 다르면 삭제 비활성 |
| `onConfirm` / `onCancel` | |
| `children` | 추가 입력 (예: 이름 확인 Input) |

시안 v0.3의 확인 창 3종은 모두 같은 모양이다(✕ 없음 — `취소`·ESC·바깥 클릭으로 닫는다). 문구는 11/16 회의 결정(`~합니다`체)을 따른다.
본문은 시안처럼 문장마다 줄을 바꾼다(`message`에 `\n`, `whitespace-pre-line`). `담당자 없음`처럼 굵게 할 낱말이 있으면 `message`에 JSX를 넘긴다. 아래 표의 ⏎는 줄바꿈이다.

| 쓰임 | 제목 | 설명 | 확인 버튼 |
| --- | --- | --- | --- |
| 업무 삭제 (S6) | 이 업무를 삭제하시겠습니까? (SPEC TASK-06-c) | '{업무 제목}' 업무가 삭제됩니다.⏎변경 이력은 남습니다 | 삭제 |
| 멤버 제거 (S7) | {이름}님을 멤버에서 제거하시겠습니까? | {이름}님이 담당하던 업무는 **담당자 없음**이 됩니다 | 제거 |
| 프로젝트 삭제 (S7) | 프로젝트를 삭제하시겠습니까? | 업무 n개가 함께 삭제되고 되돌릴 수 없습니다.⏎확인을 위해 프로젝트 이름({프로젝트 이름})을 입력해 주세요 | 삭제 (이름이 같을 때만 활성) |

```jsx
<ConfirmDialog
  open={deleting}
  title="프로젝트를 삭제하시겠습니까?"
  message={`업무 ${taskCount}개가 함께 삭제되고 되돌릴 수 없습니다.\n확인을 위해 프로젝트 이름(${project.name})을 입력해 주세요`}
  confirmLabel="삭제"
  danger
  confirmDisabled={typedName !== project.name}
  onConfirm={handleDelete}
  onCancel={() => setDeleting(false)}
>
  <Input value={typedName} onChange={(e) => setTypedName(e.target.value)} />
</ConfirmDialog>
```

### 3.8 Toast — `core/ui/ToastProvider.jsx`, `core/ui/useToast.js`

| 함수 | 쓰임 | 모양 (시안 v0.3) |
| --- | --- | --- |
| `toast.success(message)` | 저장·생성·삭제 성공 | `neutral-900` 배경 + ✓ |
| `toast.error(message)` | API 오류 (모르는 `code`면 서버 `message`) | `danger-strong` 배경 + ⚠ |
| `toast.warning(message)` | 세션 만료 | `neutral-600` 배경 + 로그아웃 아이콘 |

- 화면 아래 가운데, 3초 후 사라진다. 여러 개면 위로 쌓인다. **되돌리기 버튼은 없다**(UI-DESIGN §8-7).
- `ToastProvider`는 `main.jsx`에서 앱 전체를 감싼다.
- 세션 만료: `client.js`가 401에서 `/login?expired=1`로 보내면, 로그인 화면(T-F1-05)이 `toast.warning("로그인이 만료되었습니다. 다시 로그인해 주세요")`를 띄운다.

```jsx
const toast = useToast();
toast.success("상태를 '진행 중'으로 변경했습니다");
toast.error("상태를 바꿀 권한이 없습니다"); // SPEC TASK-06
```

### 3.9 TopBar · AppLayout — `core/layout/`

| 영역 | P0 | P1 이후 |
| --- | --- | --- |
| 왼쪽 | 로고 `동잇`("잇"만 주 색) → `/projects` | — |
| 메뉴 | `프로젝트` (현재 위치면 굵은 글자 + 밑줄) | `내 대시보드` |
| 오른쪽 | Avatar + 이름 ▾ → `로그아웃` | `내 정보 수정`(AUTH-06) |

- 로그아웃: 토큰 삭제 → `/login`. 메뉴는 바깥 클릭·ESC로 닫힌다.
- 이름은 `/users/me`(T-F1-03) 응답의 `name`을 쓴다.
- `AppLayout` = TopBar + 본문(`<Outlet />`). `App.jsx`에서 `ProtectedRoute` 안의 로그인 후 화면(S3~S8)을 감싼다. S1·S2에는 쓰지 않는다.

### 3.10 ProtectedRoute — `core/auth/ProtectedRoute.jsx` (T-F0-11)

- 로그인 상태가 아니면 `/login`으로 보낸다. 상태 복원 중에는 아무것도 그리지 않는다(Skeleton이 생기면 교체).
- 화면 접근 편의용이다. 실제 권한 차단은 백엔드가 한다.

### 3.11 EmptyState — `core/ui/EmptyState.jsx`

시안 규칙: **아이콘 + 이유 + 할 수 있는 행동 한 가지.**

| prop | 설명 |
| --- | --- |
| `variant` | `page`(기본, 화면 가운데) · `column`(칸반 컬럼 안 점선 상자) |
| `icon` | 아이콘 컴포넌트 (`page`에서만, 연한 파란 상자 안에 표시) |
| `title` | 이유 한 줄 |
| `description` | 보조 설명 |
| `action` | 버튼 하나 (선택) |

| 쓰임 | variant | 제목 | 설명 | 버튼 |
| --- | --- | --- | --- | --- |
| S3 프로젝트 0개 | `page` | 프로젝트가 없습니다 | 프로젝트를 만들어 보세요 (SPEC PRJ-02-b) | `+ 첫 프로젝트 만들기` |
| S4 컬럼 비었을 때 | `column` | 진행 중인 업무가 없습니다 | 카드의 상태를 바꾸면 여기로 옮겨집니다 | 없음 |

```jsx
<EmptyState
  icon={FolderIcon}
  title="프로젝트가 없습니다"
  description="프로젝트를 만들어 보세요"
  action={<Button onClick={openCreate}><PlusIcon />첫 프로젝트 만들기</Button>}
/>
<EmptyState variant="column" title="진행 중인 업무가 없습니다" description="카드의 상태를 바꾸면 여기로 옮겨집니다" />
```

### 3.12 Skeleton — `core/ui/Skeleton.jsx`

| 내보내기 | 설명 |
| --- | --- |
| `Skeleton` (기본) | 회색 막대 하나(`neutral-200` — `neutral-100`은 흰 카드 위에서 거의 안 보여 한 단계 진하게, 김서현 11/16 합의). 크기는 `className`으로 (`h-4 w-24`) |
| `SkeletonCard` | 시안의 카드 모양 (짧은 줄 · 긴 줄 · 짧은 줄 + 오른쪽 아래 알약) |
| `SkeletonList` | 카드 `count`장(기본 2) + 화면 읽기 프로그램에 "불러오는 중입니다" 알림. 그리드는 `className`으로 |

```jsx
if (loading) return <SkeletonList count={3} className="sm:grid-cols-2 lg:grid-cols-3" />;
```

- S3 목록, S4 보드, S6 상세에서 쓴다.

### 3.13 업무용 배지 — `features/tasks/` (T-F0-13)

표기·색 규칙은 `features/tasks/taskDisplay.js` 한 곳에 둔다(`PRIORITIES`·`STATUSES`·`getDueInfo`). 등록·상세 모달의 선택 목록도 이 상수를 쓴다.

| 컴포넌트 | props | 설명 |
| --- | --- | --- |
| `PriorityBadge` | `priority` | UI-DESIGN §6.1. 긴급 `danger` · 높음 `warning` · 보통 `info` · 낮음 `neutral` |
| `StatusSelect` | `value`, `onChange(status)`, `readOnly`, `disabled` | §6.2. 기본 `<select>` + 상태 점. 값이 바뀔 때만 `onChange`. `readOnly`는 🔒 + 글자만(권한 판단은 백엔드). 카드 클릭으로 번지지 않게 막는다 |
| `DueLabel` | `dueDate`, `status`, `today`(선택) | §6.3. `status === "DONE"`이면 표시 안 함. `today`는 미리보기·테스트에서만 넘긴다 |

```jsx
<PriorityBadge priority={task.priority} />
<DueLabel dueDate={task.due_date} status={task.status} />
<StatusSelect value={task.status} readOnly={!canChangeStatus} onChange={changeStatus} />
```

- "오늘"은 `core/utils/date.js`의 `todayKst()`(한국 날짜, API-SPEC §1.6). 브라우저 시간대를 쓰지 않는다.

### 3.14 ProjectHeader — `features/projects/ProjectHeader.jsx` (PRJ-07)

UI-DESIGN §3.2. 데이터는 받아서 그리기만 한다. S4·S7이 `getProject`·`listMembers`(`features/projects/api.js`)를 한 번 불러 넘긴다.

| props | 설명 |
| --- | --- |
| `project` | Project 응답. `null`이면 스켈레톤 |
| `members` | Member 목록(`listMembers(...).items`). 없거나 비면 아바타 묶음을 그리지 않는다 |
| `active` | `"board"` \| `"settings"` — 선택된 탭 |
| `actions` | 오른쪽 버튼 자리(선택). S4는 `+ 업무 추가` |

```jsx
<ProjectHeader
  project={project}
  members={members}
  active="board"
  actions={<Button onClick={openForm}><PlusIcon />업무 추가</Button>}
/>
```

- `프로젝트 ›`는 S3(`/projects`)로 간다. 기간이 없으면 `기간 없음`(S3 카드와 같음).
- 멤버 아바타는 최대 4개 + `+n`, 누르면 S7로 간다. Member의 `user_id`를 Avatar의 `id`로 바꿔 넘긴다.
- 탭은 `보드`·`설정` 2개이고 모든 멤버에게 보인다. 선택 탭은 `active`로 정한다(NavLink 자동 판단은 S6 주소 `/projects/:id/tasks/:taskId`에서 보드 탭이 꺼져서 쓰지 않는다).
- 진행률 바(DASH-01)는 P1. 지금은 자리만 비워 둔다.

### 3.15 ErrorPage — `core/ui/ErrorPage.jsx` (T-F0-14)

UI-DESIGN S8, NFR-09. 컴포넌트 1개에 문구만 바꿔 쓴다. TopBar는 AppLayout이 그리고, 본문에 아이콘 + 제목 + 설명 + `프로젝트 목록으로` 버튼을 그린다(EmptyState 재사용).

| props | 설명 |
| --- | --- |
| `type` | `"403"` (방패, 기본 "접근 권한이 없습니다" — SPEC PRJ-07-a) · `"404"` (나침반, 기본 "페이지를 찾을 수 없습니다") |
| `title`, `description` | 기본 문구 대신 쓸 때 (예: 칸반 404 → "프로젝트를 찾을 수 없습니다") |

```jsx
<Route path="*" element={<ErrorPage type="404" />} />
if (pageError === "403") return <ErrorPage type="403" />;
```

- 403 `NOT_PROJECT_MEMBER`(페이지 진입)에만 쓴다. 버튼 동작의 403 `FORBIDDEN`은 토스트로 보여 주고 화면은 유지한다.
- 비멤버에게 보이는 화면이라 프로젝트 이름 같은 정보를 넣지 않는다.

## 4. 남은 일

| 항목 | 담당 | 언제 |
| --- | --- | --- |
| UI-DESIGN §7 토큰 표를 v0.3 값으로 수정 (문서 → Figma 순서) | 양준석 승인 | 11/17 아침 회의 |
| ✅ `avatar-2` 확정 값 확인 → `#4F97B5` (SPEC-CHANGELOG #12) | 김서현 → 최진영 반영 | 11/17 완료 |
| ✅ ProjectHeader·MemberSelect 담당 결정 → ProjectHeader 최진영, MemberSelect 김서현 | 최진영·김서현 | 11/17 완료 |
| ✅ 세션 만료 토스트 연결 → S1에서 `?expired=1`이면 만료 토스트 (PR #16) | 최진영 | 11/17 완료 |
| 공통 컴포넌트를 실제 브라우저에서 시안과 눈으로 비교 (`/dev/components`) | 최진영 | 11/16 (5일차 공통 컴포넌트 구현) |
| ✅ S3 카드의 멤버 아바타·멤버 수 → 넣지 않음. 카드는 이름·기간·내 역할(SPEC PRJ-02-a, US-06, UI-DESIGN S3), 멤버 아바타는 S4 ProjectHeader(UI-DESIGN §S4) | 최진영 | 11/17 완료 (PR #18) |
| Modal 입력 중 확인을 브라우저 기본 확인창 대신 디자인에 맞출지, Tab 포커스 가두기 | 최진영 | P0 화면 연결 시 |
