// 아이콘 (16px 기본) — UI-DESIGN §5
// lucide(https://lucide.dev, ISC 라이선스) SVG 중 쓰는 것만 복사했다. 아이콘 라이브러리는 추가하지 않는다.
// 색은 currentColor라 글자색(text-*)을 따른다. 새 아이콘이 필요하면 lucide에서 path만 복사해 여기에 추가한다.

function Svg({ size = 16, className, children, ...rest }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={className}
      {...rest}
    >
      {children}
    </svg>
  );
}

export function ChevronDownIcon(props) {
  return (
    <Svg {...props}>
      <path d="m6 9 6 6 6-6" />
    </Svg>
  );
}

export function LogOutIcon(props) {
  return (
    <Svg {...props}>
      <path d="m16 17 5-5-5-5" />
      <path d="M21 12H9" />
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    </Svg>
  );
}

export function XIcon(props) {
  return (
    <Svg {...props}>
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </Svg>
  );
}

export function PlusIcon(props) {
  return (
    <Svg {...props}>
      <path d="M5 12h14" />
      <path d="M12 5v14" />
    </Svg>
  );
}

// 성공 토스트, 입력 성공 문구, 선택 표시
export function CheckIcon(props) {
  return (
    <Svg {...props}>
      <path d="M20 6 9 17l-5-5" />
    </Svg>
  );
}

// 마감 = 오늘·임박 (UI-DESIGN §6.3)
export function ClockIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </Svg>
  );
}

// 지연 (§6.3), 오류 토스트, 폼 오류 상자
export function TriangleAlertIcon(props) {
  return (
    <Svg {...props}>
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </Svg>
  );
}

// 안내 문구 (예: OWNER는 최소 1명 있어야 합니다)
export function InfoIcon(props) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </Svg>
  );
}

// 권한 없는 항목 🔒 (S4 카드, S6 속성)
export function LockIcon(props) {
  return (
    <Svg {...props}>
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </Svg>
  );
}

// 프로젝트 (S3 카드·빈 상태)
export function FolderIcon(props) {
  return (
    <Svg {...props}>
      <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    </Svg>
  );
}

// 프로젝트 기간, 날짜 입력
export function CalendarIcon(props) {
  return (
    <Svg {...props}>
      <path d="M8 2v4" />
      <path d="M16 2v4" />
      <rect width="18" height="18" x="3" y="4" rx="2" />
      <path d="M3 10h18" />
    </Svg>
  );
}

// 비밀번호 보기
export function EyeIcon(props) {
  return (
    <Svg {...props}>
      <path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0" />
      <circle cx="12" cy="12" r="3" />
    </Svg>
  );
}

// 비밀번호 숨기기
export function EyeOffIcon(props) {
  return (
    <Svg {...props}>
      <path d="M10.733 5.076a10.744 10.744 0 0 1 11.205 6.575 1 1 0 0 1 0 .696 10.747 10.747 0 0 1-1.444 2.49" />
      <path d="M14.084 14.158a3 3 0 0 1-4.242-4.242" />
      <path d="M17.479 17.499a10.75 10.75 0 0 1-15.417-5.151 1 1 0 0 1 0-.696 10.75 10.75 0 0 1 4.446-5.143" />
      <path d="m2 2 20 20" />
    </Svg>
  );
}

// 버튼 로딩
export function LoaderIcon({ className, ...props }) {
  return (
    <Svg className={`animate-spin ${className ?? ""}`} {...props}>
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </Svg>
  );
}

// 403 안내 화면 (S8 시안 빈 방패 — lucide shield)
export function ShieldIcon(props) {
  return (
    <Svg {...props}>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
    </Svg>
  );
}

// 404 안내 화면 (S8 시안 나침반)
export function CompassIcon(props) {
  return (
    <Svg {...props}>
      <path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z" />
      <circle cx="12" cy="12" r="10" />
    </Svg>
  );
}

export function UserPenIcon(props) {
  return (
    <Svg {...props}>
      <path d="M11.5 15H7a4 4 0 0 0-4 4v2" />
      <path d="M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z" />
      <circle cx="10" cy="7" r="4" />
    </Svg>
  );
}
