// 날짜 유틸 — ARCHITECTURE §5.1, API-SPEC §1.6
// "오늘"은 브라우저 시간대가 아니라 한국 날짜(UTC+9 고정)다. 서버의 마감 임박·지연 계산과 같은 기준을 쓴다.
// 날짜 값은 API 형식 그대로 "YYYY-MM-DD" 문자열로 다룬다.

const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

/** 한국 날짜 기준 오늘 ("YYYY-MM-DD") */
export function todayKst(now = Date.now()) {
  return new Date(now + KST_OFFSET_MS).toISOString().slice(0, 10);
}

// "YYYY-MM-DD"를 UTC 자정의 밀리초로 바꾼다. 시간대 영향 없이 날짜끼리 빼기 위해서다.
function toUtcMs(dateStr) {
  const [y, m, d] = dateStr.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

/** to - from 일수 (예: daysBetween("2026-11-17", "2026-11-20") === 3) */
export function daysBetween(from, to) {
  return Math.round((toUtcMs(to) - toUtcMs(from)) / DAY_MS);
}

/** 마감일 표기 "11/20" (UI-DESIGN §6.4) */
export function formatMonthDay(dateStr) {
  const [, m, d] = dateStr.split("-").map(Number);
  return `${m}/${d}`;
}
