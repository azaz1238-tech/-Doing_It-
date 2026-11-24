# 수용 테스트 결과 — B조 기능: 업무 권한·담당자·이력 (D10-01)

> 프로젝트: 동잇(Doing_It) | 검증: 양준석(A조) | 작성일: 2026-11-24 (Day 10)
> 기준: main `fbac9d9` (기능 동결 후, #151·#152 병합)
> 근거: SPEC §11 수용 기준 목록 · SPEC §4·§5·§6 시나리오 원문
> 수용 테스트 결과서(취합: 양준석)에 넣을 B조 몫 중 양준석 분이다. 나머지 21개(AUTH-06, TASK-01·04·05·07, CMT-01·02, LOG-03, TASK-12)는 최진영(`2026-11-24-acceptance-b-team-choi.md`). 명세가 아니며, 명세와 다르면 명세를 따른다.
## 1. 요약

- **B조가 만든 기능 시나리오 18개 모두 ✅.** 실패·버그 없음 → 이슈 등록 없음(D10-02).
- 범위: TASK-02 상태 변경, TASK-06 업무 상세·수정·삭제, TASK-03 담당자(F3), LOG-01·02 이력 기록(F4)
- TASK-03-a·b는 이전 검증표(verify.md)에 기록이 없어 이번이 첫 검증이다.
- 권한 항목(TASK-02-c·06-b·06-d)은 보안 점검 A절(`2026-11-24-security-auth.md` A10·A11)과 겹친다.

## 2. 방법

- 환경: 로컬 Docker MariaDB + 백엔드(8000) + Vite(5173)
- 새 계정과 새 프로젝트(20번 "B조 검증 00600")를 만들어 시연 데이터와 섞지 않았다.
  - 지수 `btjis00600` OWNER · 민호 `btmin00600` MEMBER · 서연 `btseo00600` MEMBER · 현우 `bthyu00600` 비멤버
  - SPEC의 "서연 = 비멤버"(TASK-03-b)는 현우로 확인했다. TASK-02-c의 서연은 명세대로 멤버다.
- **API**: Python 스크립트로 시나리오 순서대로 요청. "다른 방법으로 해도 거절"은 같은 요청을 API로 직접 보냄
- **DB**: 이력은 `task_activities`를 직접 조회, 업무 값은 `tasks`를 요청 전후로 비교
- **화면**: Chrome 일반 창(지수)·Chrome 시크릿 창(민호)·Edge(서연)에 동시에 로그인해 클릭. 상태 변경은 드롭다운과 드래그 앤 드롭(#132) 둘 다. 화면 조작 뒤 DB `task_activities`로 실제 반영을 다시 확인
- **pytest**: 전체 464 passed (`fbac9d9`), 시나리오 근거 테스트 32개 passed (4절)

## 3. 결과

### F2 업무 상태·상세

| 시나리오 | 결과 | 확인 내용 |
| --- | :-: | --- |
| TASK-02-a | ✅ | 화면: 지수가 T1을 드롭다운으로 할 일 → 진행 중 → 완료 → 할 일, 바꿀 때마다 해당 컬럼으로 이동. 이어서 끌어서 진행 중에 놓음 → 이동. DB 이력 4행. API: 같은 순서 모두 200, 완료 때 `completed_at` 생김, 할 일로 되돌리면 `null` |
| TASK-02-b | ✅ | 화면: 지수가 만들어 민호에게 배정한 T4 → 민호가 드롭다운·드래그로 진행 중 ↔ 할 일 변경, DB 이력 6행 모두 민호. API: 진행 중으로 변경 200 |
| TASK-02-c | ✅ | 화면: 서연(멤버, 작성자·담당자 아님) 화면에서 T1·T4 상태가 🔒, 카드가 끌리지 않음. API: 서연 상태 변경 403 `FORBIDDEN`, 현우(비멤버) 403 `NOT_PROJECT_MEMBER`, 상태 그대로 |
| TASK-06-a | ✅ | 화면: T1 카드 클릭 → 상세 창. 주소 새로고침·새 탭에 붙여 넣기 모두 같은 상세 창 |
| TASK-06-b | ✅ | 화면: 민호가 지수 업무 T1 상세 → `삭제` 버튼 없음. API: 민호 삭제 403 `FORBIDDEN`, 업무 조회 200(그대로) |
| TASK-06-c | ✅ | 화면: `삭제` → 확인 창 "이 업무를 삭제할까요?" → 취소하면 그대로, 다시 삭제 → 확인 → 보드에서 사라짐. DB `DELETED · 이력 T6 제목만` 1행 |
| TASK-06-d | ✅ | 화면: 담당자 민호가 T4 상세 → 상태만 드롭다운, 제목·설명·담당자·마감일·우선순위는 🔒·글자만, `삭제` 없음. API: 제목·설명·담당자·마감일·우선순위 각각, 상태+제목 함께, 삭제 → 7건 모두 403 `FORBIDDEN`, 업무 값 그대로(DB 비교) |
| TASK-06-e | ✅ | 화면: 민호가 만든 업무를 지수(OWNER)가 제목 수정 → 저장, 이어서 삭제 → 사라짐(DB `DELETED` 지수). API: 수정 200 → 삭제 204 → 조회 404 `TASK_NOT_FOUND` |
| TASK-06-f | ✅ | 지수 마감일(11/24 → 11/25), 이어서 민호 상태(할 일 → 진행 중) → 둘 다 반영, 이력 2행(`due_date` 지수 · `status` 민호). 같은 항목(상태)을 지수 완료 → 민호 할 일 순으로 저장 → 나중 값(할 일) 남음 |

### F3 담당자

| 시나리오 | 결과 | 확인 내용 |
| --- | :-: | --- |
| TASK-03-a | ✅ | 화면: 업무 등록 창·T1 상세의 담당자 선택지 모두 검증지수·검증민호·검증서연 3명(비멤버 현우 없음). API: 멤버 목록 3명, 등록·상세 창 모두 보드의 멤버 목록을 씀(`TaskFormModal.jsx:225`, `TaskDetailModal.jsx:414`) |
| TASK-03-b | ✅ | 비멤버 현우를 담당자로 등록 400 `ASSIGNEE_NOT_MEMBER` "담당자는 프로젝트 멤버여야 합니다", 수정도 400, 담당자 그대로(없음) |

### F4 이력 기록

| 시나리오 | 결과 | 확인 내용 |
| --- | :-: | --- |
| LOG-01-a | ✅ | API: 민호가 할 일 → 진행 중 → 1행 `민호 · UPDATED · status · TODO → IN_PROGRESS · 시각`. 화면: 민호가 T4를 드롭다운·드래그로 바꿀 때마다 같은 형식 1행씩(드래그도 드롭다운과 같은 이력) |
| LOG-01-b | ✅ | 지수가 상태(진행 중 → 완료)+담당자(민호 → 서연) 한 요청 → `status`·`assignee_id` 2행, 시각 같음 |
| LOG-01-c | ✅ | 삭제 204 → `DELETED` 1행(`old_value` = 삭제 전 제목). 그 업무의 이력 5행 모두 `task_id = NULL`로 남음. 프로젝트 최근 활동 API 맨 위에 `DELETED · 이력 T5` |
| LOG-01-d | ✅ | 제목만, 설명만, 같은 값(우선순위 보통·상태 할 일) 다시 보냄 → 0행. 우선순위 실제 변경(보통 → 긴급) → 1행 |
| LOG-01-e | ✅ | 상태·우선순위+비멤버 담당자 한 요청 → 400 `ASSIGNEE_NOT_MEMBER`, 권한 없음 403, 잘못된 값(`todo`) 422 → 세 경우 모두 업무 값 그대로, 이력 0행 |
| LOG-02-a | ✅ | 지수가 마감일 11/20 → 11/25 → `지수 · due_date · 2026-11-20 → 2026-11-25 · 시각` 다섯 가지 모두. 업무 이력 API 맨 위에 변경자 이름 포함 |
| LOG-02-b | ✅ | 담당 해제 → `assignee_id · 85 → NULL`, API `new_assignee: null`(이전 담당자 이름은 `old_assignee`). 삭제 → `old_value`에 삭제 전 제목 `이력 T7` |

## 4. 참고

- 자동 테스트 대조 (화면 전용인 TASK-06-a·06-c는 없음, TASK-06-f는 직접 확인만):

| 시나리오 | pytest |
| --- | --- |
| TASK-02-a | `test_patch_done_sets_and_clears_completed_at` |
| TASK-02-b | `test_patch_assignee_status_only_200` |
| TASK-02-c | `test_patch_other_member_status_403`, `test_patch_non_member_403` |
| TASK-06-b | `test_delete_by_member_not_author_403` |
| TASK-06-d | `test_patch_assignee_other_field_403`, `test_assignee_sends_assignee_id_403_not_400` |
| TASK-06-e | `test_owner_edits_and_deletes_others_task` |
| TASK-03-b | `test_create_non_member_assignee_400`, `test_patch_non_member_assignee_400` |
| LOG-01-a | `test_single_field_change_one_row` |
| LOG-01-b | `test_patch_status_and_assignee_two_activities` |
| LOG-01-c | `test_delete_records_deleted_and_keeps_history`, `test_deleted_task_titles` |
| LOG-01-d | `test_no_row_when_nothing_tracked_changes`, `test_same_assignee_no_row` |
| LOG-01-e | `test_non_member_assignee_rejected_no_row`, `test_rejected_update_no_row`, `test_record_does_not_commit` |
| LOG-02-a | `test_activity_shape` |
| LOG-02-b | `test_assignee_cleared_new_assignee_null`, `test_record_deleted_keeps_title` |

- 업무 상세의 담당자 선택지는 지금 담당자가 멤버 목록에 없으면(창을 띄워 둔 사이 멤버에서 빠진 경우) 그 사람을 현재 값으로 덧붙여 보여 준다(`TaskDetailModal.jsx:217-228`). 그 사람을 다시 고르면 서버가 400으로 거절하므로 TASK-03-b는 지켜진다.
- 검증 데이터: 프로젝트 20과 계정 4개는 개발 DB에 남겨 두었다(화면 확인용). 시연 프로젝트 4는 건드리지 않았다.
