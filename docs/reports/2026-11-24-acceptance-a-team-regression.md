# A조 수용 기준 — 자동 테스트 대조표 (D10-01)

> 프로젝트: 동잇(Doing_It) | 작성: 서승범(B조) | 작성일: 2026-11-24 (Day 10)
> 기준: main `8e6ea65` (#134 병합 후) · 근거: SPEC §11, 김서현 결과서 [2026-11-24-acceptance-a-team.md](2026-11-24-acceptance-a-team.md)
> 수용 테스트 결과서(취합: 양준석)에 붙일 참고 자료다. 명세가 아니며, 명세와 다르면 명세를 따른다.

## 1. 요약

- 김서현 결과서의 A조 시나리오 **35개를 모두** 기존 자동 테스트(pytest·Postman)와 맞춰 봤다. 결과서는 11/24에 손으로 확인한 결과이고, 이 표는 **동결 뒤 버그 수정(D10-02)이 이 시나리오를 깨뜨리면 잡아 줄 테스트가 있는지**를 적는다.
- **35개 모두 API 부분은 pytest가 지킨다.** 화면에만 있는 기준(문구 위치, 버튼 숨김·꺼짐, 이동, 토스트)은 프론트 자동 테스트 도구가 없어 결과서의 수동 확인이 유일한 근거다(§3 "화면 전용").
- API로 확인할 수 있는데 지키는 테스트가 없던 곳 3개는 `backend/tests/test_acceptance_a_team.py`에 테스트를 추가했다(§2). 기존 A조 테스트 파일은 고치지 않았다.
- 새 버그는 없다(이슈 등록 없음).
- AUTH-06(이름 수정)은 결과서 범위 밖이다. verify.md 7절에서 검증자가 양준석이고 API를 서승범이 만들었으므로 이 표에도 넣지 않았다. 화면 ⏸ 2줄이 남아 있다.

## 2. 추가한 테스트 (`backend/tests/test_acceptance_a_team.py`)

| 테스트 | 시나리오 | 비어 있던 것 | 변이 확인 |
| --- | --- | --- | --- |
| `test_auth_01_a_signup_then_login` | AUTH-01-a | 가입과 로그인을 따로만 확인했다. 가입한 계정으로 바로 로그인되는 흐름은 없었다 | 가입 때 비밀번호를 틀리게 해시하면 실패 |
| `test_prj_02_a_list_card_has_name_period_role` | PRJ-02-a | 목록 테스트는 id·역할만 확인했다. 카드의 이름·기간은 확인하지 않았다 | 응답의 시작일을 종료일로 바꾸면 실패(같은 변이를 생성·수정 테스트 3개도 잡음 — 응답 모양을 목록·상세·생성이 함께 쓰기 때문) |
| `test_prj_03_b_member_update_rejected_and_unchanged` | PRJ-03-b | MEMBER 수정은 403만 확인했다. 거절 뒤 이름·설명이 그대로인지는 확인하지 않았다 | 수정 권한을 OWNER → 모든 멤버로 바꾸면 실패 |

- 실행: pytest 전체 **401 passed**(기존 398 + 3), ruff·black 통과.

## 3. 대조표

pytest 테스트는 `backend/tests/` 기준이다. Postman은 `postman/` 컬렉션의 요청 이름이다. "화면 전용"은 자동 테스트가 없어 결과서 수동 확인만 근거인 부분이다.

### F1 회원·인증

| 시나리오 | 결과서 | pytest | Postman | 화면 전용 |
| --- | :-: | --- | --- | --- |
| AUTH-01-a | ✅ | `test_auth.py::test_signup_201_without_token`, **`test_acceptance_a_team.py::test_auth_01_a_signup_then_login`** | F1 회원가입 → 로그인 | 가입 후 토스트·`/login` 이동 |
| AUTH-01-b | ✅ | `test_auth.py::test_duplicate_login_id_409` (`jisoo01`·`JISOO01`) | F1 회원가입 - 아이디 중복 409 | 아이디 칸 아래 문구 |
| AUTH-01-c | ✅ | `test_auth.py::test_signup_validation_422` (3자·한글·특수문자·비밀번호 7자 등) | F1 회원가입 - 형식 오류 422 | 칸 아래 오류 |
| AUTH-03-a | ✅ | `test_auth.py::test_password_stored_as_bcrypt_hash`, `test_signup_201_without_token`(응답 필드), `test_login.py::test_login_200_returns_token_for_user`(응답 필드), `test_users_me.py::test_me_200_returns_user_without_password_hash`, `test_members.py::test_list_200_member_fields` | — | — |
| AUTH-02-a | ✅ | `test_login.py::test_login_200_returns_token_for_user` | F1 로그인 | 로그인 후 `/`(내 대시보드)로 이동 |
| AUTH-02-b | ✅ | `test_login.py::test_invalid_credentials_401` (틀린 비밀번호·없는 아이디 → 같은 본문) | F1 로그인 - 틀린 비밀번호 401 | 한 가지 문구 |
| AUTH-02-c | ✅ | `test_login.py::test_disabled_account_403_only_with_right_password`, `test_users_me.py::test_me_disabled_user_403` | — | 토큰 저장 안 됨 |
| AUTH-04-a | ✅ | `test_users_me.py::test_login_token_works_for_me` | F1 내 정보 | 새로고침 유지, TopBar 이름 |
| AUTH-04-b | ✅ | `test_core.py::test_expired_token_401`, `test_users_me.py::test_me_expired_token_401` | — | `/login` 이동·토큰 삭제(Axios 인터셉터) |
| AUTH-04-c | ✅ | — (로그아웃은 서버 API 없음) | — | **전부 화면** (토큰 삭제, 뒤로 가기) |
| AUTH-04-d | ✅ | `test_projects.py::test_detail_update_delete_without_token_401`, `test_core.py::test_missing_or_malformed_token_401` | F2 프로젝트 목록 - 토큰 없음 401 | `/login` 이동(ProtectedRoute) |

### F2 프로젝트

| 시나리오 | 결과서 | pytest | Postman | 화면 전용 |
| --- | :-: | --- | --- | --- |
| PRJ-01-a | ✅ | `test_projects.py::test_create_201_creator_is_owner` | F2 프로젝트 생성 | 칸반으로 이동 |
| PRJ-01-b | ✅ | `test_projects.py::test_create_name_length_422` (빈 값·공백·31자), `test_update_name_invalid_422` | F2 프로젝트 생성 - 이름 31자 422 | `31/30` 글자 수, 버튼 꺼짐 |
| PRJ-01-c | ✅ | `test_projects.py::test_create_period_reversed_422`, `test_update_end_before_saved_start_422`, `test_update_both_dates_reversed_422` | F2 프로젝트 수정 - 종료일이 시작일보다 앞 422 | 문구, 버튼 꺼짐 |
| PRJ-01-d | ✅ | `test_projects.py::test_create_description_required_422`, `test_update_description_cannot_be_cleared_422`, `test_create_description_2001_chars_422` | — | 문구, 버튼 꺼짐, Enter 제출 막힘 |
| PRJ-02-a | ✅ | `test_projects.py::test_list_only_my_projects_with_role`, **`test_acceptance_a_team.py::test_prj_02_a_list_card_has_name_period_role`** | F2 내 프로젝트 목록 | 카드 모양·기간 표기 |
| PRJ-02-b | ✅ | `test_projects.py::test_list_empty` | — | 안내 문구·`첫 프로젝트 만들기` |
| PRJ-07-a | ✅ | `test_projects.py::test_detail_non_member_403` (응답에 프로젝트 이름 없음) | F2 프로젝트 상세 - 멤버 아님 403, F3 멤버 목록 - 비멤버 403 | "접근 권한이 없습니다" 화면 |
| PRJ-03-a | ✅ | `test_projects.py::test_delete_204_cascades` (멤버·업무·이력 0행, 이후 404), `test_concurrent_delete.py` | F2 프로젝트 삭제 → 삭제 후 404 | 이름 입력 전 `삭제` 꺼짐 |
| PRJ-03-b | ✅ | `test_projects.py::test_update_by_member_403`, `test_delete_by_member_403`, **`test_acceptance_a_team.py::test_prj_03_b_member_update_rejected_and_unchanged`** | — (MEMBER 수정·삭제 요청 없음, 비멤버 삭제 403만) | 저장·삭제 버튼 숨김 |

### F3 멤버 · PRJ-08

| 시나리오 | 결과서 | pytest | Postman | 화면 전용 |
| --- | :-: | --- | --- | --- |
| PRJ-04-a | ✅ | `test_members.py::test_add_201` (추가된 사람 목록에 바로 보임) | F3 멤버 추가 - MEMBER 201 (PRJ-04-a), 확인 - 추가된 사람의 프로젝트 목록 | 토스트 |
| PRJ-04-b | ✅ | `test_members.py::test_add_unknown_login_id_404`, `test_add_inactive_user_404` | F3 멤버 추가 - 없는 아이디 404 (PRJ-04-b) | 문구 |
| PRJ-04-c | ✅ | `test_members.py::test_add_duplicate_409` | F3 멤버 추가 - 중복 409 (PRJ-04-c) | 문구 |
| PRJ-04-d | ✅ | `test_members.py::test_add_by_member_403`, `test_add_by_member_unknown_login_id_403` | F3 멤버 추가 - MEMBER가 시도 403 (PRJ-04-d) | 추가 칸 숨김 |
| PRJ-07-b | ✅ | `test_members.py::test_list_200_member_fields` (MEMBER 조회 200), `test_add_by_member_403`, `test_remove_by_member_403` | F3 멤버 목록 - MEMBER 200 | 추가 칸·제거 버튼 숨김 |
| PRJ-05-a | ✅ | `test_members.py::test_remove_204_unassigns_tasks` (담당 해제 + 이력, 제거된 사람 목록에서 사라짐, 상세 403) | F3 멤버 제거 - 업무 담당자 제거 204 (PRJ-05-a) + 확인 2건 | 확인 창 문구 |
| PRJ-05-b | ✅ | `test_members.py::test_remove_last_owner_self_400`, `test_concurrent_owners_remove_each_other` | F3 멤버 제거 - 마지막 OWNER 자신 400 (PRJ-05-b) | 문구 |
| PRJ-08-a | ✅ | `test_member_role.py::test_prj_08_a_demote_last_owner_400`, `test_prj_08_a_demote_self_after_promoting_other_200` | F3 역할 변경 (PRJ-08-a) 3건 | 강등 후 관리 기능 숨김 |

### F5 현황

| 시나리오 | 결과서 | pytest | Postman | 화면 전용 |
| --- | :-: | --- | --- | --- |
| DASH-01-a | ✅ | `test_projects.py::test_progress_list_and_detail_40_percent`, `test_progress_no_tasks_0_percent` | — | "40% · 4/10 완료" 표기 |
| DASH-02-a | ✅ | `test_assignee_stats.py::test_dash_02_a_counts_with_unassigned` | F2-tasks 담당자별 현황 - 멤버 200, 합계 = 업무 수 (DASH-02-a) | 표 모양, "담당자 없음" 맨 아래 |
| DASH-03-a | ✅ | `test_stats.py::test_dash_03_a` (오늘·+3일·+4일·완료·마감일 없음 경계) | — | — |
| DASH-04-a | ✅ | `test_my_tasks.py::test_dash_04_a_order_and_project`, `test_due_soon_boundary` | — | 지연·임박 강조 |
| DASH-04-b | ✅ | `test_my_tasks.py::test_dash_04_b_done_excluded_and_empty` | — | 안내 문구·`프로젝트로 가기` |

### TASK-08 드래그 앤 드롭 (P2, 기능 동결 예외)

| 시나리오 | 결과서 | pytest | Postman | 화면 전용 |
| --- | :-: | --- | --- | --- |
| TASK-08-a | ✅ | `test_tasks_api.py::test_patch_status_and_assignee_two_activities` (드래그도 같은 `PATCH` 상태 변경 → 이력 1행) | F2-tasks 상태 변경 - 담당자 200 | **끌어 놓기 자체**(HTML5 드래그) |
| TASK-08-b | ✅ | `test_tasks_api.py::test_patch_other_member_status_403` | F2-tasks 상태 변경 - 작성자도 담당자도 아닌 MEMBER 403 | 카드가 끌리지 않음, 원래 컬럼 복귀·문구 |

## 4. 참고

- 화면 전용 기준이 가장 많은 곳은 F1 이동·토큰 처리(AUTH-04-b·c·d)와 버튼 숨김(PRJ-03-b·04-d·07-b)이다. 동결 뒤 프론트를 고치면 이 칸은 다시 손으로 확인해야 한다.
- Postman에는 MEMBER의 프로젝트 수정·삭제 403 요청(PRJ-03-b)이 없다. pytest가 지키므로 동결일에 추가하지 않았다(선택).
