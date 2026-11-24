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

/**
 * dateStr에서 n일 뒤(음수면 앞) 날짜 "YYYY-MM-DD". 달·해가 바뀌어도 시간대 영향 없이 계산한다.
 * 달력·간트(TASK-11)의 날짜 칸을 만들 때 쓴다. 예: addDays("2026-11-30", 1) === "2026-12-01"
 */
export function addDays(dateStr, n) {
  return new Date(toUtcMs(dateStr) + n * DAY_MS).toISOString().slice(0, 10);
}

/** 요일 번호 0(일)~6(토). 이름은 WEEKDAYS[weekdayOf(d)]. 예: weekdayOf("2026-11-24") === 2(화) */
export function weekdayOf(dateStr) {
  return new Date(toUtcMs(dateStr)).getUTCDay();
}

/** 마감일 표기 "11/20" (UI-DESIGN §6.4) */
export function formatMonthDay(dateStr) {
  const [, m, d] = dateStr.split("-").map(Number);
  return `${m}/${d}`;
}

/** 프로젝트 기간 "11.10 – 11.19" (UI-DESIGN §6.4). 날짜는 선택 항목이라 없는 쪽은 비운다. 둘 다 없으면 "" */
export function formatPeriod(start, end) {
  if (!start && !end) return "";
  const md = (d) => {
    const [, m, day] = d.split("-");
    return `${Number(m)}.${day}`;
  };
  return `${start ? md(start) : ""} – ${end ? md(end) : ""}`.trim();
}

/** 요일 이름 (일요일 시작). 달력·간트 머리글에도 쓴다 */
export const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const JUST_NOW_MS = 60 * 1000;

/**
 * 서버 시각(UTC `Z`)을 한국 시간으로 — UI-DESIGN §6.4
 * 1분 미만이면 "방금 전"(SPEC LOG-03-a), 오늘이면 "오늘 09:41", 어제면 "어제 18:22", 그 밖은 "11/10 14:20"
 */
export function formatDateTime(isoString, now = Date.now()) {
  const timeMs = new Date(isoString).getTime();
  // PC 시계가 서버보다 조금 늦으면 차이가 음수가 된다. 그때도 "방금 전"으로 본다.
  if (now - timeMs < JUST_NOW_MS) return "방금 전";
  const kst = new Date(timeMs + KST_OFFSET_MS);
  const day = kst.toISOString().slice(0, 10);
  const time = kst.toISOString().slice(11, 16);
  const diff = daysBetween(day, todayKst(now));
  if (diff === 0) return `오늘 ${time}`;
  if (diff === 1) return `어제 ${time}`;
  return `${formatMonthDay(day)} ${time}`;
}

/** 마감일 입력창 옆 표기 "2026-11-14 (토)" — UI-DESIGN §6.4 */
export function formatDateWithWeekday(dateStr) {
  return `${dateStr} (${WEEKDAYS[weekdayOf(dateStr)]})`;
}
