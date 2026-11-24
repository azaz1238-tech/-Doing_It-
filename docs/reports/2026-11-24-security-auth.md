# 보안 점검 — 인증·권한 (D10-03 A절)

> 프로젝트: 동잇(Doing_It) | 점검일: 2026-11-24 | 기준: main `5e18360`(기능 동결 시점) | 담당: 양준석
> 근거: CONSTITUTION §6·§9, CLAUDE.md §5, API-SPEC §1.2·§1.5
> 다른 절: DB·입력값(서승범) → [2026-11-24-security-db-input.md](2026-11-24-security-db-input.md) · XSS·토큰 노출(최진영) → [2026-11-24-security-xss-token.md](2026-11-24-security-xss-token.md) · 취합 → [2026-11-24-security-summary.md](2026-11-24-security-summary.md)
> 결과: **통과** · **문제**(이슈 번호) · **한계**(이번 범위 밖, 아래 표)

## 점검 방법

- **pytest:** `backend`에서 전체 실행 → **464 passed** (기존 권한·인증 테스트 포함)
- **직접 호출:** 로컬 서버(:8000, 시드 데이터)에 Python 스크립트로 요청
  - 비멤버 계정 1개(`secchk98348`)를 새로 가입시켜 jisoo01의 프로젝트 1·업무 10·댓글에 접근
  - 댓글은 시드에 없어서 jisoo01로 임시 댓글을 만들어 확인한 뒤 삭제함
- **코드:** 라우터 전수, `core/auth.py`·`core/security.py`·`core/config.py`·`core/exceptions.py`·`app/main.py`·`services/auth_service.py`·`services/permissions.py`

## A. 인증·권한

| # | 점검 항목 | 확인 방법 | 결과 | 근거·비고 |
| :-: | --- | --- | :-: | --- |
| A1 | 인증 없이 부를 수 있는 API는 회원가입·로그인·`/api/health`뿐 | `openapi.json`의 28개 경로·메서드를 토큰 없이 호출 | 통과 | 25개 401. 나머지 3개만 401이 아님: health 200, signup·login 422(빈 본문) |
| A2 | 토큰 없음·Bearer 형식 틀림·서명 틀림·만료 → 모두 401 `UNAUTHORIZED` | pytest + 직접 호출 8가지 | 통과 | Bearer 빠짐·Basic·빈 값·서명 바꿈·쓰레기 문자열·만료 모두 401. `test_core.py`, `test_users_me.py` |
| A3 | HS256 고정 → `alg: none` 위조 거절, `exp`·`sub` 없는 토큰 거절 | 코드 + pytest + 위조 토큰 호출 | 통과 | `alg: none` 401, 서명은 그대로 두고 `sub`만 바꾼 토큰 401. `test_none_algorithm_token_rejected`, `test_token_without_exp_or_sub_401` |
| A4 | `JWT_SECRET_KEY`가 비었거나 32자 미만이면 서버 시작 안 함. `.env`는 Git에 없음 | 키를 바꿔 앱 시작 + `git ls-files`·`check-ignore` | 통과 | 짧은 키·빈 키 모두 `ConfigError`로 멈춤(메시지에 키 값 없음). `.env`는 `.gitignore:10`, 추적 안 됨 |
| A5 | 비밀번호는 bcrypt 해시로만 저장, 응답에 `password_hash` 없음 | 가입·로그인·`/me`·프로젝트·멤버 응답 | 통과 | 응답 전체에 "password" 글자 0건. 로그인 응답은 `access_token`·`token_type`·`expires_in`뿐 |
| A6 | 로그인 실패 문구가 "아이디 없음"과 "비밀번호 틀림"에서 같음, 응답 시간 차이 없음 | 각 5회 호출 | 통과 | 둘 다 401 `INVALID_CREDENTIALS` 같은 문구. 평균 183ms / 180ms(더미 해시 비교) |
| A7 | 비활성 계정: 로그인 403 `ACCOUNT_DISABLED`(비밀번호가 맞을 때만), 가지고 있던 토큰도 403 | pytest | 통과 | `test_disabled_account_403_only_with_right_password`, `test_me_disabled_user_403`, `test_disabled_account_403_on_task_api` |
| A8 | 역할 비교는 `permissions.py`에서만 | 코드 검색 | 통과 | `permissions.py` 밖 2곳은 비교가 아님(프로젝트 생성 시 OWNER 값 지정) |
| A9 | 프로젝트 하위 리소스는 멤버 확인 먼저 → 비멤버 403 | pytest(403) | 통과 | 업무·멤버·이력·댓글·통계 각 `non_member_403` 테스트 |
| A10 | ID 바꿔치기: 남의 프로젝트·업무·댓글 id로 조회·수정·삭제 → 거절, 데이터 노출 없음 | 비멤버 계정으로 직접 호출 18건 | 통과 | 18건 모두 403 `NOT_PROJECT_MEMBER`(프로젝트 조회·수정·삭제, 업무 목록·생성·조회·수정·삭제, 멤버 목록·추가, 이력, 통계 2종, 댓글 목록·작성·수정·삭제). 자기를 OWNER로 추가하는 요청도 403. 2xx 0건, 업무·댓글 내용 그대로. 비멤버의 `/me/tasks`(달력) 0건 |
| A11 | MEMBER: 남의 업무 수정·삭제 403, 담당자는 상태만, 댓글은 본인 것만 | pytest | 통과 | `test_patch_other_member_status_403`, `test_patch_assignee_other_field_403`, `test_delete_by_member_not_author_403`, `test_comment_permissions_order`. 드래그 앤 드롭도 같은 `PATCH /tasks/{id}` |
| A12 | 마지막 OWNER 제거·강등 400 `LAST_OWNER`, 동시 요청에도 유지 | pytest(동시성) | 통과 | `test_prj_08_a_demote_last_owner_400`, `test_remove_last_owner_self_400`, `test_concurrent_owners_remove_each_other`(#72) |
| A13 | 검사 순서 401 → 422 → 404 → 403 → 400 | pytest | 통과 | `test_add_without_token_invalid_body_401`, `test_non_member_bad_body_422_before_403`, `test_target_not_member_404`, `test_assignee_sends_assignee_id_403_not_400` |
| A14 | CORS: `FRONTEND_ORIGIN` 하나만, 자격 증명 끔 | 코드 + 사전 요청(OPTIONS) | 통과 | `localhost:5173` 200 허용, 다른 출처 400·허용 헤더 없음. `allow-credentials` 없음 |
| A15 | 500 응답에 스택트레이스·SQL·내부 경로 없음 | 코드 + pytest | 통과 | 공통 처리기가 `INTERNAL_ERROR` 고정 문구만 보냄, 상세는 서버 로그에만. `test_core.py` 강제 오류 테스트. #142 때 실제 500 응답도 같은 형식 |

## 알려진 한계 (이번 범위 밖 — 발표 "향후 계획" 후보)

| # | 한계 | 이유·영향 |
| :-: | --- | --- |
| L1 | 로그인 시도 횟수 제한 없음 | 범위 밖, 로컬 시연. 무차별 대입 방어 없음 |
| L2 | 생성 개수·요청 속도 제한 없음 | 명세에 상한 없음 |
| L3 | 로그아웃해도 토큰이 만료(2시간)까지 유효 | Access Token만 사용 (API-SPEC §8) |
| L4 | 토큰을 localStorage에 저장 → XSS가 생기면 탈취 가능 | 기술 스택 결정. C절(XSS 차단)이 전제 |
| L5 | HTTPS 아님, `/docs`(Swagger) 공개 (직접 호출 200 확인) | 로컬 시연용. 배포하면 HTTPS·문서 비공개 필요 |
| L6 | 없는 프로젝트는 404, 남의 프로젝트는 403이라 id 존재 여부는 알 수 있음 (내용은 안 보임) | 명세의 검사 순서(404 → 403)대로 동작. id가 연속 번호 |

## 결과 요약

- 점검 항목 **15개: 통과 15 / 문제 0**, 한계 6개(범위 밖)
- 새로 등록할 이슈: 없음
- 점검 중 로컬 DB에 남은 것: 점검용 계정 `secchk98348` 1개 (시드 다시 넣으면 사라짐). 임시 댓글은 삭제함
