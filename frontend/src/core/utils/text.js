// 글자 수 유틸 — 서버(Python `len`)와 같게 유니코드 코드 포인트로 센다.
// JS의 `str.length`는 UTF-16 단위라 이모지 하나(😀)를 2로 센다 → 서버가 받는 값을 화면이 막는다(#49, D7-01).

/** 글자 수 (코드 포인트 기준). 앞뒤 공백 제거는 부르는 쪽에서 정한다. */
export const countChars = (value) => [...String(value ?? "")].length;
