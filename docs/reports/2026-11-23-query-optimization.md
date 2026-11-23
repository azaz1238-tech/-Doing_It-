# 쿼리 최적화 기록 — N+1·인덱스 (D9-03)

> 작성: 서승범 · 기준: 2026-11-23, main `1bface7` + 댓글 PR #100 `feat/CMT-01-comments`(리비전 `0003`) · 측정 DB: 테스트 DB `doing_it_test`(MariaDB 10.11)
> 근거: DATABASE-DESIGN §7·§8.1, ARCHITECTURE §4. 명세가 아니며, 명세와 다르면 명세를 따른다.
> 댓글 테이블·`ix_tasks_project_due`는 PR #100에 있다. **이 문서는 #100 병합 뒤에 병합한다.** 개발 DB(`doing_it`, 시연 데이터)에서는 측정하지 않았다.

## 1. 결론

- **N+1 없음.** 목록을 돌려주는 화면 API 7개(9가지 요청)를 확인했다. 응답 행이 1~2건에서 10~20건으로 늘어도 요청 1번의 SQL 수는 같다(§2).
- **목록 쿼리는 모두 인덱스를 쓴다.** API가 실제로 실행한 SQL을 EXPLAIN했다. 업무 4,020행, 이력 4,060행, 댓글 4,020행 기준이다(§3). 인덱스 없이 테이블을 다 읽는 경우(`ALL`)는 행이 21개 이하인 `users`·`projects` 두 곳뿐이다. 이 두 곳은 옵티마이저가 고른 것이다(§3.3).
- **§8.1 인덱스 표와 실제 DB가 일치한다.** 표에는 있었지만 어느 리비전에도 없던 `ix_tasks_project_due`는 `0003`에 넣었다(SPEC-CHANGELOG #25).
- **새로 고칠 쿼리는 없다.** 일부러 하지 않은 것은 §4에 이유와 함께 적었다.

## 2. N+1 점검 — 요청 1번의 SQL 수

**측정 방법.** 측정은 SQLAlchemy `before_cursor_execute` 이벤트로 했다. 요청 1번 동안 실행된 SQL을 센다. 데이터는 다음처럼 만들었다.
- 사람 1명일 때와 10명일 때를 비교했다.
- 사람마다 **자기가 작성하고 자기가 담당하는** 업무를 1개씩 만든다. 그래서 행마다 작성자와 담당자가 모두 다른 사람이다. 사용자를 행마다 따로 조회하면 SQL 수가 늘어난다.
- 이력은 업무 생성과 상태 변경으로 생긴다.
- 사람마다 첫 업무에 댓글 1개를 단다.
- 사람마다 다른 작성자로 첫 사람에게 업무를 1개씩 맡긴다(내 업무용).

| API | 적을 때 SQL | 응답 행 | 많을 때 SQL | 응답 행 | N+1 방지 방법 | 테스트로 고정 |
| --- | :-: | :-: | :-: | :-: | --- | --- |
| `GET /projects/{id}/tasks?status=` (칸반 컬럼) | 8 | 1 | 8 | 10 | `selectinload(assignee, creator)` | — |
| 같은 API + 필터 `q`·`priority` (TASK-07) | 7 | 1 | 7 | 10 | 같음 | — |
| `GET /projects/{id}/members` | 5 | 2 | 5 | 11 | 사용자 조인 1번 | — |
| `GET /projects/{id}/activities` (최근 이력) | 7 | 3 | 7 | 20 (전체 30) | 사용자·업무 제목 묶음 조회 2번 | `test_query_count_constant` |
| `GET /tasks/{id}/comments` | 7 | 1 | 7 | 10 | `selectinload(author)` | `test_comment_list_query_count_constant` (#100) |
| `GET /projects/{id}/stats/deadlines` (DASH-03) | 6 | due_soon 1 | 6 | due_soon 10 | `selectinload(assignee, creator)` | — |
| `GET /users/me/tasks` (DASH-04) | 6 | 2 | 6 | 11 | `selectinload(assignee, creator)` | — |
| `GET /projects` (내 프로젝트) | 4 | 2 | 4 | 11 | 진행률을 프로젝트 묶음으로 1번에 계산 | — |

- **SQL 수의 차이.** 요청마다 공통으로 쓰는 쿼리가 다르다. 인증(사용자 조회)은 모든 요청에 있다. 프로젝트 하위 API에는 권한 확인(프로젝트·멤버십 2번)이 더해지고, 목록 API에는 전체 개수(count)가 더해진다.
  - 칸반 컬럼(8)과 필터(7)는 1번 차이가 나는데, 이 차이도 행 수와 관계없이 일정하다. 칸반 쪽에 인증 직후 사용자 PK 조회가 한 번 더 있다(측정 로그 기준, 원인은 따로 조사하지 않음).
- **이 측정에서 뺀 것.** 업무 이력(`GET /tasks/{id}/activities`)은 업무 하나의 이력이라 이 데이터로는 행이 늘지 않는다. 다만 최근 이력과 같은 변환 함수(`_to_out`)를 쓴다.

## 3. 인덱스 — 실제 DB 대조와 EXPLAIN

### 3.1 §8.1 표와 실제 인덱스

`information_schema.STATISTICS`로 확인했다(리비전 `0003` 적용 후).

| 테이블 | §8.1 인덱스 | 실제 | 비고 |
| --- | --- | :-: | --- |
| users | `uq_users_login_id` (login_id) | ✅ | |
| project_members | `uq_project_members_project_user` (project_id, user_id) | ✅ | |
| project_members | `ix_project_members_user_id` (user_id) | ✅ | |
| tasks | `ix_tasks_project_status` (project_id, status) | ✅ | FK `project_id`도 이 인덱스를 쓴다 |
| tasks | `ix_tasks_assignee_status` (assignee_id, status) | ✅ | FK `assignee_id`도 이 인덱스를 쓴다 |
| tasks | `ix_tasks_project_due` (project_id, due_date) | ✅ | **`0003`에서 추가** (#25) |
| task_activities | `ix_task_activities_task` (task_id, created_at, id) | ✅ | |
| task_activities | `ix_task_activities_project` (project_id, created_at, id) | ✅ | |
| task_comments | `ix_task_comments_task` (task_id, created_at) | ✅ | `0003` |

그 밖의 인덱스는 PK와, 다른 인덱스가 받쳐 주지 않는 FK 컬럼에 InnoDB가 자동으로 만든 것(`fk_..._created_by_users`, `fk_..._user_id_users`)뿐이다. 겹치는 인덱스는 없다. §8.1의 "앞쪽 컬럼과 겹치면 따로 만들지 않는다"가 지켜졌다.

### 3.2 EXPLAIN — API가 실행한 SQL 그대로

**측정 방법.** 측정 데이터는 다음과 같다.
- 프로젝트 20개, 사람 20명, 프로젝트당 업무 200개
- 마감일은 오늘 ±30일
- 상태와 우선순위는 고르게 섞었다
- 업무마다 이력 1행, 댓글 1개
- 넣은 뒤 `ANALYZE TABLE`을 실행했다

각 API를 호출하면서 실행된 SQL과 파라미터를 잡아, 같은 값으로 `EXPLAIN`했다. 아래 표에는 목록·집계 쿼리만 적는다. 인증·권한 확인(PK·UNIQUE로 `const`)과 count는 뺐다. count는 같은 인덱스를 `Using index`로 읽는다.

| API | 쿼리 | type | 쓴 인덱스 | 예상 행 | Extra |
| --- | --- | --- | --- | :-: | --- |
| 칸반 컬럼 | tasks: project_id + status, `CASE` 우선순위 정렬 | ref | `ix_tasks_project_status` | 87 | Using index condition; Using where; Using filesort |
| 필터 `q` | tasks: project_id + `title LIKE concat('%', ?, '%') ESCAPE` + priority | ref | `ix_tasks_project_due` (앞 컬럼 project_id) | 220 | Using where; Using filesort |
| 최근 이력 | task_activities: project_id, `created_at DESC, id DESC` LIMIT 20 | ref | `ix_task_activities_project` | 260 | Using where (정렬 작업 없음) |
| 업무 이력 | task_activities: task_id, 최신순 | ref | `ix_task_activities_task` | 3 | Using where (정렬 작업 없음) |
| 댓글 | task_comments: task_id, `created_at, id` | ref | `ix_task_comments_task` | 1 | Using where (정렬 작업 없음) |
| 마감 임박·지연 | tasks: project_id + 미완료 + 마감일 있음 + `due_date <= 오늘+3` | range | `ix_tasks_project_due` | 142 | Using index condition; Using where |
| 내 업무 | tasks ⋈ projects ⋈ project_members: assignee_id + 미완료 | range / eq_ref / eq_ref | `ix_tasks_assignee_status` / PRIMARY / `uq_project_members_project_user` | 142 / 1 / 1 | Using index condition; Using filesort |
| 멤버 목록 | project_members ⋈ users: project_id | ref / eq_ref | `uq_project_members_project_user` / PRIMARY | 21 / 1 | Using where; Using filesort |
| 내 프로젝트 | project_members: user_id → projects 조인 | ref / ALL | `ix_project_members_user_id` / — | 20 / 20 | Using filesort (§3.3) |
| 내 프로젝트 진행률 | tasks: `project_id IN (...)` 상태별 개수 | range | `ix_tasks_project_status` | 4,020 | Using where; **Using index** (테이블을 읽지 않음) |

- **정렬 작업이 없는 쿼리.** 이력·댓글은 인덱스 순서가 곧 정렬 순서다. 그래서 정렬 작업(filesort) 없이 앞에서 필요한 만큼만 읽는다.
  - 댓글 인덱스는 (task_id, created_at)뿐이다. 그래도 InnoDB 보조 인덱스는 끝에 PK(id)를 품고, MariaDB는 이 PK를 정렬에 쓴다(`extended_keys`, 기본 켜짐). 그래서 `ORDER BY created_at, id`에도 filesort가 없다.
- **마감 임박·지연.** `ix_tasks_project_due`로 그 프로젝트의 마감일 범위만 읽는다(range).
- **내 프로젝트 진행률.** 필요한 컬럼(project_id, status)이 모두 인덱스 안에 있다. 그래서 행 수가 많아도 테이블 본문을 읽지 않는다.

### 3.3 `ALL`(전체 읽기)이 나온 곳

| 쿼리 | 이유 | 판단 |
| --- | --- | --- |
| `selectinload`의 `users WHERE id IN (…)` | 측정 데이터의 사용자가 21명이다. 그중 대부분을 한 번에 가져오므로 PK로 하나씩 찾는 것보다 다 읽는 쪽이 싸다고 옵티마이저가 골랐다. 업무 이력·댓글처럼 1명만 찾을 때는 `const`(PK)다 | 정상(테이블이 작을 때의 선택). 가져올 id가 적으면 PK를 쓴다는 것을 같은 측정의 1명 조회(`const`)로 확인 |
| 내 프로젝트: `projects` 조인 | 측정 사용자가 20개 프로젝트 모두의 멤버라, 필요한 프로젝트가 테이블 전부다 | 정상. 소속 프로젝트가 일부면 PK 조인(`eq_ref`)이 된다 |

## 4. 하지 않은 것과 이유

| 항목 | 이유 |
| --- | --- |
| 칸반 정렬(우선순위 → 마감일)의 filesort | §8.1 결정대로 둔다. 컬럼 하나가 수십 건 수준이라 메모리 정렬로 충분하다. 우선순위는 `CASE` 식(`priority_order`)이라 인덱스로 정렬할 수 없다 |
| 검색 `q`(`LIKE '%키워드%'`)용 인덱스 | 앞에 `%`가 붙은 부분 일치는 B-tree 인덱스를 쓸 수 없다. 대신 project_id로 먼저 좁혀 그 프로젝트의 업무(측정에서 220건)만 훑는다. FULLTEXT는 한글 처리와 명세 범위 때문에 쓰지 않는다 |
| 내 업무의 `status != 'DONE'` | 부정 조건이라 인덱스 범위가 넓어진다. 하지만 앞 컬럼(assignee_id)으로 이미 한 사람의 업무로 좁혀진다 |
| 목록 count 쿼리 | 페이지마다 개수를 한 번 더 센다. 같은 인덱스만 읽고(`Using index`) 행 수가 작아 그대로 둔다 |

## 5. 남은 제안 (선택)

- **N+1 테스트 추가.** 업무 목록(칸반), 마감 임박, 내 업무에도 "행이 늘어도 SQL 수가 같다" 테스트를 넣으면 `selectinload`가 빠지는 실수를 막을 수 있다. 이력·댓글과 같은 방식이다. 업무 목록은 서승범, DASH-03·04는 양준석 코드다.
- **측정 스크립트를 넣지 않은 이유.** 데이터 4천 행을 넣어 테스트 시간이 늘어나서 저장소에 넣지 않았다. 다시 측정하려면 §2·§3.2의 데이터 구성대로 만들고, `before_cursor_execute`로 잡은 SQL을 `EXPLAIN`하면 된다.
