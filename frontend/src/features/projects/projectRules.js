// 프로젝트 입력 규칙 — PRJ-01(생성)·PRJ-03(수정). 수정도 생성과 같은 규칙이다(API-SPEC §5.2).
// 문구는 SPEC 따옴표 문구 = 백엔드 schemas/project.py 문구. 생성 모달(S3)과 설정(S7)이 같이 쓴다.

export const NAME_MAX = 30;
export const NAME_ERROR = "프로젝트 이름은 1~30자로 입력해 주세요"; // PRJ-01-b
export const PERIOD_ERROR = "종료일은 시작일 이후여야 합니다"; // PRJ-01-c
// 설명 필수 — PRJ-01-d (11/22 팀장 결정, SPEC-CHANGELOG #21). 백엔드 DESCRIPTION_MESSAGE와 같은 문구
export const DESCRIPTION_ERROR = "프로젝트 설명을 입력해 주세요";

// 글자 수는 공통 유틸을 쓴다(서버 Python len과 같게 — 이모지도 1자)
export { countChars } from "../../core/utils/text";

// 역할 배지 색 — S3 카드의 내 역할, S7 멤버 목록의 역할 (토큰 색만, COMPONENTS §3.1)
export const ROLE_STYLES = {
  OWNER: "bg-primary-soft text-primary",
  MEMBER: "bg-neutral-100 text-neutral-600",
};
