# API 명세서 (API-SPEC.md)

> 프로젝트: 동잇(Doing_It) — 팀 협업 프로젝트 관리 시스템 | 버전: v0.3 (P2 비밀번호 변경·회원 탈퇴·프로젝트 나가기, 댓글 300자, 체크리스트 10개) · v0.2 (업무 수정 권한 세분화, 마감일 오늘 = 임박) | 작성일: 2026-11-11
> 근거: [CONSTITUTION.md](./CONSTITUTION.md) §6·§7·§8 · [REQUIREMENTS.md](./REQUIREMENTS.md) v0.7 · [USER-STORIES.md](./USER-STORIES.md) v0.7 · [DATABASE.md](./DATABASE.md) v0.4
> 상위 문서와 다르면 상위 문서를 따르고 이 문서를 고친다. API를 바꿀 때는 **이 문서를 먼저 수정**한다(CONSTITUTION 7-5).
> 각 API에 근거 기능 ID와 우선순위를 표시한다. **P0 API부터 구현하고, P1·P2 API는 P0 게이트 통과 후에 만든다.**

## 1. 공통 규칙

### 1.1 기본

| 항목 | 규칙 |
| --- | --- |
| 기본 주소 | `http://localhost:8000` (개발). 경로 앞에 접두어를 붙이지 않는다 (§9 결정 필요 1) |
| 형식 | 요청·응답 모두 `application/json; charset=utf-8` |
| 이름 | 경로는 복수형 명사 + 소문자 케밥(`checklist-items`), JSON 필드는 `snake_case` |
| 시각 | `DATETIME` 값은 UTC, ISO 8601 + `Z` (예: `2026-11-11T05:30:00Z`) |
| 날짜 | `DATE` 값(`start_date`, `end_date`, `due_date`)은 `YYYY-MM-DD` |
| 알 수 없는 필드 | 요청 본문에 정의되지 않은 필드가 있으면 422 (`project_id`, `created_by` 등을 바꾸지 못하게 막음) |

### 1.2 인증

- 회원가입·로그인을 **제외한 모든 API**는 `Authorization: Bearer <access_token>` 헤더가 필요하다 (CONSTITUTION 6-1).
- 토큰: JWT, 알고리즘 `HS256`, 만료 **2시간**(`ACCESS_TOKEN_EXPIRE_MINUTES=120`). 담는 값은 `sub`(사용자 id 문자열), `exp`만 둔다.
- 요청마다 `sub`로 사용자를 조회한다. 사용자가 없거나 탈퇴했으면(`deleted_at` 있음, P2) 401 `UNAUTHORIZED`, 비활성(`is_active=0`)이면 403 `ACCOUNT_DISABLED`.
- 로그아웃 API는 없다. 프론트에서 localStorage의 토큰을 지운다 (US-03).

### 1.3 목록 응답과 페이지네이션 (NFR-05)

```json
{ "items": [ ... ], "total": 42, "page": 1, "size": 20 }
```

| 쿼리 | 기본값 | 규칙 |
| --- | --- | --- |
| `page` | 1 | 1 이상 |
| `size` | 20 | 1~100 (§9 결정 필요 2) |

### 1.4 오류 응답 (NFR-04)

```json
{ "code": "ASSIGNEE_NOT_MEMBER", "message": "담당자는 프로젝트 멤버여야 합니다." }
```

입력 검증 실패(422)만 필드별 오류를 덧붙인다 (NFR-03).

```json
{
  "code": "VALIDATION_ERROR",
  "message": "입력값을 확인해 주세요.",
  "errors": [
    { "field": "title", "message": "업무 제목은 1~30자로 입력해 주세요." }
  ]
}
```

### 1.5 검사 순서

모든 프로젝트 하위 API는 아래 순서로 검사한다. 앞 단계에서 실패하면 뒤는 검사하지 않는다.

1. 요청 형식 검증 → 422
2. 토큰 검증 → 401 / 비활성 계정 403
3. 대상 리소스 존재 → 404
4. 프로젝트 멤버인지 → 403 `NOT_PROJECT_MEMBER` (CONSTITUTION 6-4)
5. 역할·작성자 권한 → 403 `FORBIDDEN` (`require_project_role(...)`로만 검사)
6. 업무 규칙 → 400

## 2. 오류 코드 목록

| HTTP | code | 의미 | 사용처 |
| :-: | --- | --- | --- |
| 400 | `ASSIGNEE_NOT_MEMBER` | 담당자가 프로젝트 멤버가 아님 | 업무 등록·수정 |
| 400 | `LAST_OWNER` | 마지막 OWNER를 제거하거나 MEMBER로 바꾸려 함 | 멤버 제거·역할 변경, 프로젝트 나가기·회원 탈퇴(P2) |
| 400 | `WRONG_PASSWORD` | 현재 비밀번호가 틀림 (P2) | 비밀번호 변경, 회원 탈퇴 |
| 400 | `CHECKLIST_LIMIT_EXCEEDED` | 체크리스트 항목이 이미 10개 (P2) | 체크리스트 항목 추가 |
| 401 | `UNAUTHORIZED` | 토큰 없음·형식 오류·만료·사용자 없음 | 인증 필요 API 전체 |
| 401 | `INVALID_CREDENTIALS` | 아이디 또는 비밀번호가 틀림(어느 쪽인지 알리지 않음) | 로그인 |
| 403 | `ACCOUNT_DISABLED` | 비활성화된 계정 | 로그인, 인증 필요 API 전체 |
| 403 | `NOT_PROJECT_MEMBER` | 프로젝트 멤버가 아님 | 프로젝트 하위 API 전체 |
| 403 | `FORBIDDEN` | 멤버지만 권한이 없음(OWNER 전용, 본인 것만 가능 등) | 프로젝트 수정·삭제, 멤버 관리, 업무 수정·삭제, 댓글 수정·삭제, 체크리스트 변경 |
| 404 | `USER_NOT_FOUND` | 해당 아이디의 회원이 없음 | 멤버 추가 |
| 404 | `PROJECT_NOT_FOUND` | 프로젝트 없음 | 프로젝트 API |
| 404 | `MEMBER_NOT_FOUND` | 프로젝트 멤버가 아닌 사용자를 대상으로 함 | 멤버 제거·역할 변경 |
| 404 | `TASK_NOT_FOUND` | 업무 없음 | 업무 API |
| 404 | `COMMENT_NOT_FOUND` | 댓글 없음 (P1) | 댓글 API |
| 404 | `CHECKLIST_ITEM_NOT_FOUND` | 체크리스트 항목 없음 (P2) | 체크리스트 API |
| 404 | `NOT_FOUND` | 없는 경로 | 공통 |
| 409 | `LOGIN_ID_ALREADY_EXISTS` | 이미 사용 중인 아이디 | 회원가입 |
| 409 | `ALREADY_MEMBER` | 이미 프로젝트 멤버 | 멤버 추가 |
| 422 | `VALIDATION_ERROR` | 입력 검증 실패 | 공통 |
| 500 | `INTERNAL_ERROR` | 서버 오류(상세 내용은 응답에 넣지 않음) | 공통 |

## 3. API 목록

| 우선순위 | 메서드 | 경로 | 설명 | 권한 | 기능 ID |
| :-: | --- | --- | --- | --- | --- |
| P0 | POST | `/auth/signup` | 회원가입 | 없음 | AUTH-01, 03 |
| P0 | POST | `/auth/login` | 로그인 | 없음 | AUTH-02 |
| P0 | GET | `/users/me` | 내 정보 조회 | 로그인 | AUTH-04 |
| P1 | PATCH | `/users/me` | 내 이름 수정 | 로그인 | AUTH-06 |
| P2 | PATCH | `/users/me/password` | 비밀번호 변경 | 로그인 | AUTH-07 |
| P2 | DELETE | `/users/me` | 회원 탈퇴 | 로그인 | AUTH-08 |
| P0 | POST | `/projects` | 프로젝트 생성 | 로그인 | PRJ-01 |
| P0 | GET | `/projects` | 내 프로젝트 목록 | 로그인 | PRJ-02 (진행률은 DASH-01 P1) |
| P0 | GET | `/projects/{project_id}` | 프로젝트 상세 | 멤버 | PRJ-07 |
| P0 | PATCH | `/projects/{project_id}` | 프로젝트 수정 | OWNER | PRJ-03 |
| P0 | DELETE | `/projects/{project_id}` | 프로젝트 삭제 | OWNER | PRJ-03 |
| P0 | GET | `/projects/{project_id}/members` | 멤버 목록 | 멤버 | PRJ-07 |
| P0 | POST | `/projects/{project_id}/members` | 멤버 추가 | OWNER | PRJ-04 |
| P0 | DELETE | `/projects/{project_id}/members/{user_id}` | 멤버 제거 (P2: 본인이면 나가기) | OWNER (P2: 또는 본인) | PRJ-05, PRJ-09 |
| P1 | PATCH | `/projects/{project_id}/members/{user_id}` | 멤버 역할 변경 | OWNER | PRJ-08 |
| P0 | GET | `/projects/{project_id}/tasks` | 업무 목록(칸반) | 멤버 | TASK-05 (필터는 TASK-07 P1) |
| P0 | POST | `/projects/{project_id}/tasks` | 업무 등록 | 멤버 | TASK-01, 03, 04, LOG-01 |
| P0 | GET | `/tasks/{task_id}` | 업무 상세 | 멤버 | TASK-06 |
| P0 | PATCH | `/tasks/{task_id}` | 업무 수정·상태 변경 | OWNER·작성자(전체), 담당자(상태만) | TASK-02, 03, 06, LOG-01, 02 |
| P0 | DELETE | `/tasks/{task_id}` | 업무 삭제 | OWNER 또는 작성자 | TASK-06, LOG-01 |
| P1 | GET | `/tasks/{task_id}/comments` | 댓글 목록 | 멤버 | CMT-01 |
| P1 | POST | `/tasks/{task_id}/comments` | 댓글 작성 | 멤버 | CMT-01 |
| P1 | PATCH | `/comments/{comment_id}` | 댓글 수정 | 작성자 | CMT-02 |
| P1 | DELETE | `/comments/{comment_id}` | 댓글 삭제 | 작성자 | CMT-02 |
| P1 | GET | `/tasks/{task_id}/activities` | 업무 변경 이력 | 멤버 | LOG-03 |
| P1 | GET | `/projects/{project_id}/activities` | 프로젝트 최근 이력 | 멤버 | LOG-03 |
| P1 | GET | `/projects/{project_id}/stats/assignees` | 담당자별 상태별 업무 수 | 멤버 | DASH-02 |
| P1 | GET | `/projects/{project_id}/stats/deadlines` | 마감 임박·지연 업무 | 멤버 | DASH-03 |
| P1 | GET | `/users/me/tasks` | 내 업무(전체 프로젝트) | 로그인 | DASH-04 |
| P2 | GET | `/tasks/{task_id}/checklist-items` | 체크리스트 목록 | 멤버 | TASK-09 |
| P2 | POST | `/tasks/{task_id}/checklist-items` | 체크리스트 항목 추가 | OWNER·작성자·담당자 | TASK-09 |
| P2 | PATCH | `/checklist-items/{item_id}` | 항목 수정·체크 | OWNER·작성자·담당자 | TASK-09 |
| P2 | DELETE | `/checklist-items/{item_id}` | 항목 삭제 | OWNER·작성자·담당자 | TASK-09 |

P2 중 TASK-08(드래그 앤 드롭)·TASK-10(업무 진행률)·TASK-11(달력)은 새 API 없이 기존 API를 확장한다(§8). AUTH-05·PRJ-06·ADM-01은 착수할 때 이 문서에 추가한다.

## 4. 공통 객체

**User**
```json
{ "id": 1, "login_id": "jisoo01", "name": "지수", "system_role": "USER", "created_at": "2026-11-11T05:30:00Z" }
```
`password_hash`, `is_active`는 어떤 응답에도 넣지 않는다 (CONSTITUTION 6-7).

**UserBrief** — 다른 객체 안에 들어가는 사용자 요약: `{ "id": 2, "login_id": "minho", "name": "민호" }`

**Project**
```json
{
  "id": 10,
  "name": "동잇 개발",
  "description": "11월 팀 프로젝트",
  "start_date": "2026-11-10",
  "end_date": "2026-11-26",
  "my_role": "OWNER",
  "created_at": "2026-11-11T05:30:00Z",
  "updated_at": "2026-11-11T05:30:00Z"
}
```
P1(DASH-01)에서 `"progress": { "total": 10, "done": 4, "percent": 40 }`을 추가한다.

**Member**
```json
{ "user_id": 2, "login_id": "minho", "name": "민호", "role": "MEMBER", "joined_at": "2026-11-11T06:00:00Z" }
```

**Task**
```json
{
  "id": 100,
  "project_id": 10,
  "title": "로그인 API 구현",
  "description": "JWT 발급까지",
  "status": "IN_PROGRESS",
  "priority": "HIGH",
  "assignee": { "id": 2, "login_id": "minho", "name": "민호" },
  "due_date": "2026-11-14",
  "created_by": { "id": 1, "login_id": "jisoo01", "name": "지수" },
  "completed_at": null,
  "created_at": "2026-11-11T05:30:00Z",
  "updated_at": "2026-11-12T01:00:00Z"
}
```
- `assignee`는 담당자가 없으면 `null`.
- 값 목록: `status` = `TODO` | `IN_PROGRESS` | `DONE`, `priority` = `LOW` | `MEDIUM` | `HIGH` | `URGENT`.

## 5. P0 API 상세

### 5.1 인증 (AUTH)

#### POST `/auth/signup` — 회원가입 · AUTH-01, AUTH-03 · US-01

요청
```json
{ "login_id": "jisoo01", "password": "password123", "name": "지수" }
```

| 필드 | 규칙 |
| --- | --- |
| `login_id` | 필수. 앞뒤 공백 제거 후 소문자로 바꾸고 `^[a-z0-9]{4,20}$` 검사 |
| `password` | 필수. 8자 이상. bcrypt 해시로만 저장 |
| `name` | 필수. 앞뒤 공백 제거 후 1~50자 |

응답 `201` — User

| 오류 | 상황 |
| --- | --- |
| 409 `LOGIN_ID_ALREADY_EXISTS` | 같은 아이디가 있음(대소문자만 다른 경우 포함) |
| 422 `VALIDATION_ERROR` | 형식 위반 |

#### POST `/auth/login` — 로그인 · AUTH-02 · US-02

요청 `{ "login_id": "jisoo01", "password": "password123" }` (`login_id`는 소문자로 바꿔 조회)

응답 `200`
```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 7200 }
```

| 오류 | 상황 |
| --- | --- |
| 401 `INVALID_CREDENTIALS` | 없는 아이디 또는 틀린 비밀번호 |
| 403 `ACCOUNT_DISABLED` | 비활성 계정 (비밀번호가 맞을 때만 알려 준다) |

#### GET `/users/me` — 내 정보 조회 · AUTH-04 · US-03

응답 `200` — User. 새로고침 시 로그인 상태 복원에 쓴다. 토큰이 유효하지 않으면 401 → 프론트는 토큰 삭제 후 로그인 화면으로 이동.

### 5.2 프로젝트 (PRJ)

#### POST `/projects` — 프로젝트 생성 · PRJ-01 · US-05

요청
```json
{ "name": "동잇 개발", "description": "11월 팀 프로젝트", "start_date": "2026-11-10", "end_date": "2026-11-26" }
```

| 필드 | 규칙 |
| --- | --- |
| `name` | 필수. 앞뒤 공백 제거 후 1~30자 |
| `description` | 선택. 문자열 또는 `null` |
| `start_date`, `end_date` | 선택. 둘 다 있으면 `end_date >= start_date` (위반 시 422, "종료일은 시작일 이후여야 합니다") |

응답 `201` — Project (`my_role: "OWNER"`)
처리: `projects` 생성과 생성자의 `project_members(role=OWNER)` 추가를 **한 트랜잭션**으로 한다.

#### GET `/projects` — 내 프로젝트 목록 · PRJ-02 · US-06

쿼리: `page`, `size`
응답 `200` — `Project` 목록. 내가 멤버인 프로젝트만, `created_at` 최신순.

#### GET `/projects/{project_id}` — 프로젝트 상세 · PRJ-07

응답 `200` — Project
오류: 404 `PROJECT_NOT_FOUND`, 403 `NOT_PROJECT_MEMBER`

#### PATCH `/projects/{project_id}` — 프로젝트 수정 · PRJ-03 · US-08

요청: `name`, `description`, `start_date`, `end_date` 중 바꿀 필드만. 규칙은 생성과 같다(날짜 비교는 저장될 최종 값 기준).
응답 `200` — Project
오류: 404, 403 `NOT_PROJECT_MEMBER`, 403 `FORBIDDEN`(MEMBER), 422

#### DELETE `/projects/{project_id}` — 프로젝트 삭제 · PRJ-03 · US-08

응답 `204`. 멤버·업무·댓글·이력이 CASCADE로 함께 삭제된다. 이름을 입력하는 확인 절차는 화면에서만 한다.
오류: 404, 403 `NOT_PROJECT_MEMBER`, 403 `FORBIDDEN`

### 5.3 멤버 (PRJ)

#### GET `/projects/{project_id}/members` — 멤버 목록 · PRJ-07 · US-07

쿼리: `page`, `size`
응답 `200` — `Member` 목록. OWNER 먼저, 같은 역할은 `joined_at` 순. 업무 담당자 선택지로도 쓴다.
오류: 404, 403 `NOT_PROJECT_MEMBER`

#### POST `/projects/{project_id}/members` — 멤버 추가 · PRJ-04 · US-07

요청 `{ "login_id": "minho", "role": "MEMBER" }` (`role` = `OWNER` | `MEMBER`, `login_id`는 소문자로 바꿔 조회)
응답 `201` — Member

| 오류 | 상황 |
| --- | --- |
| 403 `FORBIDDEN` | MEMBER가 추가 시도 |
| 404 `USER_NOT_FOUND` | 가입하지 않은 아이디 |
| 409 `ALREADY_MEMBER` | 이미 멤버 (DB `UNIQUE(project_id, user_id)`로도 막음) |

#### DELETE `/projects/{project_id}/members/{user_id}` — 멤버 제거 · PRJ-05 · US-09

응답 `204`. 아래를 **한 트랜잭션**으로 처리한다.
1. 제거 대상이 OWNER이고 OWNER가 1명뿐이면 400 `LAST_OWNER` (OWNER 자신을 제거하는 경우 포함)
2. 이 프로젝트에서 대상이 담당하던 업무의 `assignee_id`를 NULL로 바꾸고, 업무마다 `task_activities`에 1행 기록(`field=assignee_id`, 변경자 = 제거한 OWNER)
3. `project_members` 행 삭제

오류: 403 `FORBIDDEN`(MEMBER), 404 `MEMBER_NOT_FOUND`, 400 `LAST_OWNER`

**P2 확장 (PRJ-09 프로젝트 나가기):** `user_id`가 요청자 본인이면 MEMBER도 호출할 수 있다. 처리(1~3단계)와 `LAST_OWNER` 규칙은 같고, 이력의 변경자는 나간 본인이다. P0 구현에서는 MEMBER의 호출을 모두 403으로 막는다.

### 5.4 업무 (TASK)

#### GET `/projects/{project_id}/tasks` — 업무 목록(칸반) · TASK-05 · US-12

| 쿼리 | 우선순위 | 설명 |
| --- | :-: | --- |
| `status` | P0 | `TODO` \| `IN_PROGRESS` \| `DONE`. 칸반은 컬럼마다 1번씩 호출 |
| `page`, `size` | P0 | 기본 20, 최대 100 |
| `q` | P1 | 제목 키워드(부분 일치) — TASK-07 |
| `assignee_id` | P1 | 담당자. `none`이면 담당자 미지정만 — TASK-07 |
| `priority` | P1 | 우선순위 — TASK-07 |
| `due_from`, `due_to` | P1 | 마감일 범위(양 끝 포함) — TASK-07, 달력(TASK-11)도 사용 |

정렬(고정): 우선순위 높은 순(`URGENT` → `LOW`) → 마감일 빠른 순(마감일 없음은 뒤) → `id` 순.
응답 `200` — `Task` 목록
오류: 404 `PROJECT_NOT_FOUND`, 403 `NOT_PROJECT_MEMBER`

#### POST `/projects/{project_id}/tasks` — 업무 등록 · TASK-01, 03, 04 · US-11

요청
```json
{ "title": "로그인 API 구현", "description": "JWT 발급까지", "assignee_id": 2, "due_date": "2026-11-14", "priority": "HIGH" }
```

| 필드 | 규칙 |
| --- | --- |
| `title` | 필수. 앞뒤 공백 제거 후 1~30자 |
| `description` | 선택 |
| `assignee_id` | 선택. 이 프로젝트 멤버만 가능(아니면 400 `ASSIGNEE_NOT_MEMBER`) |
| `due_date` | 선택. 과거 날짜·프로젝트 기간 밖 날짜도 허용 |
| `priority` | 선택. 기본 `MEDIUM` |

`status`는 받지 않으며 항상 `TODO`로 생성한다.
응답 `201` — Task
처리: 업무 생성과 `task_activities`(`action=CREATED`, `field=null`) 기록을 **한 트랜잭션**으로 한다.

#### GET `/tasks/{task_id}` — 업무 상세 · TASK-06 · US-14

응답 `200` — Task
오류: 404 `TASK_NOT_FOUND`, 403 `NOT_PROJECT_MEMBER`(업무가 속한 프로젝트 기준)

#### PATCH `/tasks/{task_id}` — 업무 수정·상태 변경 · TASK-02, 03, 06, LOG-01, 02 · US-13, US-14, US-18

요청: 바꿀 필드만 보낸다.
```json
{ "status": "IN_PROGRESS", "assignee_id": null }
```

| 필드 | 규칙 |
| --- | --- |
| `title` | 1~30자. `null` 불가 |
| `description` | 문자열 또는 `null` |
| `status` | 어느 방향으로든 변경 가능(TASK-02) |
| `assignee_id` | 멤버 id 또는 `null`(담당 해제) |
| `due_date` | 날짜 또는 `null`(마감일 해제) |
| `priority` | `null` 불가 |

권한 (REQUIREMENTS 권한 매트릭스):

| 요청자 | 바꿀 수 있는 필드 |
| --- | --- |
| OWNER | 전부 |
| MEMBER + 업무 작성자 | 전부 |
| MEMBER + 담당자(작성자 아님) | `status`만. 다른 필드가 하나라도 있으면 요청 전체를 403 `FORBIDDEN`으로 거절 |
| 그 외 MEMBER | 없음 → 403 `FORBIDDEN` |

처리(**한 트랜잭션**):
1. `status`가 `DONE`이 되면 `completed_at`을 현재 시각(UTC)으로, `DONE`에서 다른 상태로 바뀌면 `NULL`로 바꾼다.
2. 값이 실제로 바뀐 `status`, `assignee_id`, `due_date`, `priority`마다 `task_activities`에 1행씩 기록한다(`action=UPDATED`, `old_value`/`new_value`는 문자열, `null`은 NULL). 같은 값으로 바꾸면 기록하지 않는다.
3. `title`, `description` 변경은 이력 대상이 아니다(LOG-01 범위).
4. 이력 기록이 실패하면 업무 변경도 취소된다.
5. 동시 수정은 막지 않는다. 요청에 보낸 필드만 바꾸므로 서로 다른 필드는 둘 다 반영되고, 같은 필드는 나중 요청이 남는다(잠금·버전 검사 없음, SPEC Q5).

응답 `200` — Task
오류: 404, 403 `NOT_PROJECT_MEMBER`, 403 `FORBIDDEN`, 400 `ASSIGNEE_NOT_MEMBER`, 422

#### DELETE `/tasks/{task_id}` — 업무 삭제 · TASK-06, LOG-01 · US-14

권한: OWNER는 모든 업무, MEMBER는 **본인이 만든 업무만**(아니면 403 `FORBIDDEN`).
처리(**한 트랜잭션**): `task_activities`에 `action=DELETED`, `old_value=삭제 전 제목` 1행 기록 → 업무 삭제. 이력의 `task_id`는 FK `ON DELETE SET NULL`로 NULL이 되어 남는다. 댓글·체크리스트는 CASCADE로 삭제된다.
응답 `204`
오류: 404, 403 `NOT_PROJECT_MEMBER`, 403 `FORBIDDEN`

## 6. P1 API 상세

#### PATCH `/users/me` — 내 이름 수정 · AUTH-06 · US-04
요청 `{ "name": "지수" }` (1~50자) → `200` User

#### PATCH `/projects/{project_id}/members/{user_id}` — 역할 변경 · PRJ-08 · US-26
요청 `{ "role": "OWNER" }` → `200` Member
오류: 403 `FORBIDDEN`, 404 `MEMBER_NOT_FOUND`, 400 `LAST_OWNER`(마지막 OWNER를 MEMBER로 변경)

#### 댓글 · CMT-01, CMT-02 · US-17

| API | 요청 | 응답 | 비고 |
| --- | --- | --- | --- |
| GET `/tasks/{task_id}/comments` | `page`, `size` | `200` Comment 목록 | 작성 시각 오래된 순 |
| POST `/tasks/{task_id}/comments` | `{ "content": "..." }` | `201` Comment | 앞뒤 공백 제거 후 1~300자(빈 댓글·초과 422) |
| PATCH `/comments/{comment_id}` | `{ "content": "..." }` | `200` Comment | 작성자만. OWNER도 남의 댓글은 403 `FORBIDDEN` |
| DELETE `/comments/{comment_id}` | — | `204` | 작성자만 |

Comment: `{ "id", "task_id", "user": UserBrief, "content", "created_at", "updated_at" }`

#### 변경 이력 · LOG-03 · US-27, US-19

| API | 쿼리 | 정렬 |
| --- | --- | --- |
| GET `/tasks/{task_id}/activities` | `page`, `size` | 최신순 |
| GET `/projects/{project_id}/activities` | `page`, `size`(화면은 `size=20`) | 최신순, 삭제된 업무 이력 포함 |

Activity
```json
{
  "id": 501, "task_id": 100, "user": { "id": 2, "login_id": "minho", "name": "민호" },
  "action": "UPDATED", "field": "due_date", "old_value": "2026-11-20", "new_value": "2026-11-25",
  "created_at": "2026-11-12T01:00:00Z"
}
```
삭제된 업무의 이력은 `task_id: null`이다.

#### GET `/projects/{project_id}/stats/assignees` — 담당자별 현황 · DASH-02 · US-21
응답 `200`
```json
{ "items": [
  { "assignee": { "id": 2, "login_id": "minho", "name": "민호" }, "todo": 3, "in_progress": 1, "done": 5 },
  { "assignee": null, "todo": 2, "in_progress": 0, "done": 0 }
] }
```
집계 결과라 페이지네이션하지 않는다(§9 결정 필요 3). `assignee: null`은 담당자 미지정.

#### GET `/projects/{project_id}/stats/deadlines` — 마감 임박·지연 · DASH-03 · US-22
응답 `200` — `{ "overdue": [Task...], "due_soon": [Task...] }`
- 대상: `status <> DONE`이고 `due_date`가 있는 업무. 마감일 순.
- `overdue`: `due_date < 오늘`, `due_soon`: `오늘 <= due_date <= 오늘 + 3일`. **마감일이 오늘이면 임박**(SPEC Q1 결정). "오늘"의 기준 시간대는 §9 결정 필요 4.

#### GET `/users/me/tasks` — 내 업무 대시보드 · DASH-04 · US-23
쿼리: `page`, `size`
응답 `200` — `Task` 목록 + 각 항목에 `"project": { "id", "name" }`, `"alert": "OVERDUE" | "DUE_SOON" | null`
대상: 나에게 할당된 미완료 업무. 정렬: 지연 → 임박 → 나머지, 각 그룹 안에서 마감일 빠른 순(없음은 뒤).

## 7. P2 API 상세

#### 체크리스트 · TASK-09 · US-28

| API | 요청 | 응답 |
| --- | --- | --- |
| GET `/tasks/{task_id}/checklist-items` | — | `200` `{ "items": [ChecklistItem...] }` (`position` 순, 페이지네이션 없음) |
| POST `/tasks/{task_id}/checklist-items` | `{ "content": "..." }` (1~100자) | `201` ChecklistItem (맨 아래에 추가). 이미 10개면 400 `CHECKLIST_LIMIT_EXCEEDED` |
| PATCH `/checklist-items/{item_id}` | `{ "content"?, "is_done"? }` | `200` ChecklistItem |
| DELETE `/checklist-items/{item_id}` | — | `204` |

ChecklistItem: `{ "id", "task_id", "content", "is_done", "position", "created_at", "updated_at" }`
권한: 조회는 업무가 속한 프로젝트의 멤버 누구나, 추가·수정·삭제는 OWNER·업무 작성자·업무 담당자만(그 외 403 `FORBIDDEN`). 체크리스트 변경은 `task_activities`에 기록하지 않는다.

#### PATCH `/users/me/password` — 비밀번호 변경 · AUTH-07 · US-31

요청 `{ "current_password": "...", "new_password": "..." }` (새 비밀번호 8자 이상)
응답 `204`
오류: 400 `WRONG_PASSWORD`, 422
> ⚠️ Access Token만 쓰므로 변경 전에 발급된 토큰은 만료(최대 2시간)까지 유효하다. 다른 기기 강제 로그아웃은 범위 밖이다.

#### DELETE `/users/me` — 회원 탈퇴 · AUTH-08 · US-32

요청 `{ "password": "..." }`
응답 `204`
처리(**한 트랜잭션**):
1. 비밀번호 확인(틀리면 400 `WRONG_PASSWORD`)
2. 마지막 OWNER인 프로젝트가 하나라도 있으면 400 `LAST_OWNER`
3. 모든 프로젝트에서 나가기(5.3 멤버 제거 1~3단계를 프로젝트마다 수행, 담당 업무 해제 + 이력 기록)
4. `users` 행은 지우지 않고 `deleted_at` 기록, `is_active=0`, `name`을 "탈퇴한 사용자"로 변경. `login_id`는 그대로 두어 재사용을 막는다.

탈퇴 후 그 아이디로 로그인하면 401 `INVALID_CREDENTIALS`, 남아 있는 토큰으로 호출하면 401 `UNAUTHORIZED`.
> 사용자 행을 실제로 지우지 않는 이유: 업무 작성자·이력 변경자 FK가 `NOT NULL`이라 지우면 이력이 사라진다(CONSTITUTION 8-3 이력 보존).

## 8. 기존 API 확장 계획 (P1·P2)

| 기능 ID | 우선순위 | 확장 내용 |
| --- | :-: | --- |
| DASH-01 | P1 | `GET /projects`, `GET /projects/{id}` 응답에 `progress` 추가 |
| TASK-07 | P1 | `GET /projects/{id}/tasks`에 `q`, `assignee_id`, `priority`, `due_from`, `due_to` 추가 |
| TASK-08 | P2 | `PATCH /tasks/{id}`에 `position` 추가 |
| TASK-10 | P2 | Task 응답에 `"checklist": { "total": 5, "done": 2 }` 추가(항목이 없으면 `null`) |
| TASK-11 | P2 | 새 API 없음. `GET /projects/{id}/tasks?due_from=&due_to=`로 한 달치 조회 |

## 9. 결정 필요 (팀 확인 후 이 절을 지운다)

| # | 항목 | 초안의 선택 | 다른 선택지 |
| :-: | --- | --- | --- |
| 1 | 경로 접두어 | 없음(`/projects`) — CONSTITUTION 예시와 같음 | `/api/v1/projects` (프론트 라우트와 구분, 버전 관리) |
| 2 | 목록 `size` 최대값 | 100 | 명세에는 기본 20만 있음. 칸반·멤버 목록이 한 번에 받기 위해 상한 필요 |
| 3 | 집계 응답 페이지네이션 | 담당자별 현황, 마감 임박·지연, 체크리스트는 하지 않음 | 모든 목록에 적용(NFR-05 문구 그대로) |
| 4 | 마감 판단 "오늘" 기준 | 한국 시간(Asia/Seoul) 날짜 | UTC 날짜(오전 9시 전에 하루 차이 발생) |
| 5 | 422 응답 형식 | `code`·`message` + `errors[]` (FastAPI 기본 `detail` 형식을 공통 예외 처리에서 변환) | FastAPI 기본 형식 유지 |
| 6 | 담당자 변경 이력 값 | `old_value`·`new_value`에 사용자 id 문자열 저장, 화면에서 이름으로 변환 | 변경 시점 이름을 저장(제거된 멤버도 표시 가능) |
| 7 | CORS | 허용 주소를 `.env`의 `FRONTEND_ORIGIN`으로 관리(`.env.example`에 추가 필요) | — |
| 8 | 로그인 요청 형식 | JSON 본문 | FastAPI `OAuth2PasswordRequestForm`(form 형식, Swagger 인증 버튼 연동) |

## 10. pytest 필수 대상 (CONSTITUTION 9-1·9-2)

P0 핵심 API(인증·권한·업무 CRUD)는 아래 경우를 반드시 포함한다.

| 구분 | 반드시 넣을 경우 |
| --- | --- |
| 인증 | 가입 성공 201, 아이디 중복 409(대소문자만 다른 경우 포함), 형식 위반 422, 로그인 성공·실패 401, 비활성 403, 토큰 없음·만료 401, 응답에 `password_hash` 없음 |
| 권한 | 비멤버의 프로젝트·업무 조회 403, MEMBER의 프로젝트 수정·삭제 403, MEMBER의 멤버 추가·제거 403, MEMBER의 타인 업무 수정·삭제 403, 담당자 MEMBER의 상태 변경 성공·다른 필드 변경 403, 작성자도 담당자도 아닌 MEMBER의 상태 변경 403, 마지막 OWNER 제거 400 |
| 업무 CRUD | 등록 201 + `CREATED` 이력 1건, 비멤버 담당자 400, 제목 31자 422, 상태+담당자 동시 변경 시 이력 2건, `DONE` 전환 시 `completed_at` 기록·해제, 삭제 후 이력 `task_id` NULL로 유지 |
