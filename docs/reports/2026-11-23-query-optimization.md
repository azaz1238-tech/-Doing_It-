# 쿼리 최적화 기록 — N+1·인덱스 (D9-03)

> 작성: 서승범 · 기준: 2026-11-23, main `50eaf37` + 댓글 브랜치 `feat/CMT-01-comments`(리비전 `0003`) · 측정 DB: 테스트 DB `doing_it_test`(MariaDB 10.11)
> 근거: DATABASE-DESIGN §7·§8.1, ARCHITECTURE §4. 명세가 아니며, 명세와 다르면 명세를 따른다.
> 개발 DB(`doing_it`, 시연 데이터)에서는 측정하지 않았다.

## 1. 결론

- **N+1 없음.** 목록을 돌려주는 화면 API 8개 모두, 행 수가 1개 → 10개로 늘어도 요청 1번의 SQL 수가 같다(§2).
- **주요 쿼리 9개 모두 인덱스를 쓴다.** 전체 테이블 스캔(`ALL`)은 없다(§3). 업무 4,000행·이력 4,000행·댓글 4,000행에서 확인.
- §8.1 인덱스 표와 실제 DB가 일치한다. 표에 있었지만 어느 리비전에도 없던 `ix_tasks_project_due`는 리비전 `0003`에 넣었다(SPEC-CHANGELOG #24).
- 새로 고칠 쿼리는 없다. 일부러 하지 않은 것은 §4에 이유와 함께 적었다.

## 2. N+1 점검 — 요청 1번의 SQL 수

측정 방법: SQLAlchemy `before_cursor_execute` 이벤트로 요청 1번 동안 실행된 SQL 수를 센다. 작성자·담당자가 행마다 다른 사람이 되게 만들어(사용자 조회가 행마다 생기면 숫자가 늘도록) 1행일 때와 10행일 때를 비교했다.

| API | 1행 | 10행 | N+1 방지 방법 | 테스트로 고정 |
| --- | :-: | :-: | --- | --- |
| `GET /projects/{id}/tasks` (칸반 컬럼) | 7 | 7 | `selectinload(assignee, creator)` | — (이번 측정) |
| `GET /projects/{id}/tasks` + 필터 (TASK-07) | 7 | 7 | 같음, 조건만 추가 | — (이번 측정) |
| `GET /projects` (내 프로젝트) | 4 | 4 | 목록 쿼리 1번 | — |
| `GET /projects/{id}/members` | 5 | 5 | 목록 쿼리 1번 | — |
| `GET /projects/{id}/activities` (최근 이력) | 7 | 7 | 사용자·업무 제목 묶음 조회 2번 | `test_query_count_constant` |
| `GET /tasks/{id}/comments` | 7 | 7 | `selectinload(author)` | `test_comment_list_query_count_constant` |
| `GET /projects/{id}/stats/deadlines` (DASH-03) | 6 | 6 | `selectinload(assignee, creator)` | — |
| `GET /users/me/tasks` (DASH-04) | 5 | 5 | `selectinload(assignee, creator)` | — |

- SQL 수에는 공통으로 인증(사용자 조회), 권한 확인(`require_project_role`), 전체 개수(count)가 들어 있다. 행 수와 관계없이 고정이다.
- 이력·댓글은 쿼리 수가 늘면 실패하는 테스트가 있다. 업무 목록은 `selectinload`를 빼면 숫자가 행 수만큼 늘어나는 구조라 같은 테스트를 추가할 만하다(§5).

## 3. 인덱스 — 실제 DB 대조와 EXPLAIN

### 3.1 §8.1 표와 실제 인덱스

`information_schema.STATISTICS`로 확인(리비전 `0003` 적용 후).

| 테이블 | §8.1 인덱스 | 실제 | 비고 |
| --- | --- | :-: | --- |
| users | `uq_users_login_id` (login_id) | ✅ | |
| project_members | `uq_project_members_project_user` (project_id, user_id) | ✅ | |
| project_members | `ix_project_members_user_id` (user_id) | ✅ | |
| tasks | `ix_tasks_project_status` (project_id, status) | ✅ | FK `project_id`도 이 인덱스를 쓴다 |
| tasks | `ix_tasks_assignee_status` (assignee_id, status) | ✅ | FK `assignee_id`도 이 인덱스를 쓴다 |
| tasks | `ix_tasks_project_due` (project_id, due_date) | ✅ | **`0003`에서 추가** (#24) |
| task_activities | `ix_task_activities_task` (task_id, created_at, id) | ✅ | |
| task_activities | `ix_task_activities_project` (project_id, created_at, id) | ✅ | |
| task_comments | `ix_task_comments_task` (task_id, created_at) | ✅ | `0003` |

그 밖의 인덱스는 FK용으로 InnoDB가 만든 것(`fk_..._created_by_users`, `fk_..._user_id_users`)과 PK뿐이다. 겹치는 인덱스는 없다(§8.1 "앞쪽 컬럼과 겹치면 따로 만들지 않는다" 지켜짐).

### 3.2 EXPLAIN (업무 4,000 · 이력 4,000 · 댓글 4,000 · 멤버 420행, `ANALYZE TABLE` 후)

| 쿼리 (쓰는 API) | type | 쓴 인덱스 | 예상 행 | Extra |
| --- | --- | --- | :-: | --- |
| 칸반 컬럼: project_id + status, 우선순위 정렬 | ref | `ix_tasks_project_status` | 67 | Using filesort |
| 검색 `q`: project_id + `title LIKE '%..%'` | ref | `ix_tasks_project_due`(앞 컬럼 project_id) | 200 | Using where |
| 마감 임박·지연: project_id + 미완료 + `due_date <= 오늘+3` | range | `ix_tasks_project_due` | 44 | Using index condition |
| 내 업무: assignee_id + 미완료 (+ projects 조인) | range / eq_ref | `ix_tasks_assignee_status` / PRIMARY | 141 / 1 | |
| 업무 이력: task_id, 최신순 20건 | ref | `ix_task_activities_task` | 1 | filesort 없음 |
| 프로젝트 최근 이력: project_id, 최신순 20건 | ref | `ix_task_activities_project` | 200 | filesort 없음 |
| 댓글: task_id, 오래된 순 | ref | `ix_task_comments_task` | 1 | filesort 없음 |
| 멤버십 확인 (모든 요청) | const | `uq_project_members_project_user` | 1 | |
| 내 프로젝트 | ref | `ix_project_members_user_id` | 20 | |

- 이력·댓글은 인덱스 순서가 곧 정렬 순서라 정렬 작업(filesort) 없이 앞에서 20건만 읽는다.
- 댓글 인덱스는 (task_id, created_at)이지만 InnoDB 보조 인덱스는 끝에 PK(id)를 품으므로 `ORDER BY created_at, id`도 인덱스 순서로 처리된다.
- 마감 임박·지연은 `ix_tasks_project_due`로 그 프로젝트의 마감일 범위만 읽는다(range, 200건 중 44건). 이 인덱스가 없으면 project_id로 시작하는 다른 인덱스로 프로젝트 업무를 모두 읽고 마감일을 거르게 된다.

## 4. 하지 않은 것과 이유

| 항목 | 이유 |
| --- | --- |
| 칸반 정렬(우선순위 → 마감일)의 filesort | §8.1 결정대로 둔다. 컬럼 하나가 수십 건 수준이라 메모리 정렬로 충분하고, 우선순위는 `FIELD()` 식이라 인덱스로 정렬할 수 없다 |
| 검색 `q`(`LIKE '%키워드%'`)용 인덱스 | 앞에 `%`가 붙은 부분 일치는 B-tree 인덱스를 쓸 수 없다. 프로젝트 조건(project_id)으로 먼저 좁혀 그 프로젝트 업무(수십~수백 건)만 훑으므로 충분하다. FULLTEXT는 한글 형태소·명세 범위 밖 |
| 내 업무의 `status != 'DONE'` | 부정 조건이라 인덱스 범위가 넓어지지만, 앞 컬럼(assignee_id)으로 이미 한 사람의 업무로 좁혀진다 |
| 목록 count 쿼리 | 페이지마다 개수를 한 번 더 센다. 같은 인덱스를 쓰고 행 수가 작아 그대로 둔다 |

## 5. 남은 제안 (선택)

- 업무 목록(칸반)·마감 임박·내 업무에도 "행이 늘어도 SQL 수가 같다" 테스트를 추가하면 `selectinload`가 빠지는 실수를 막을 수 있다(이력·댓글과 같은 방식). 업무 목록은 서승범, DASH-03·04는 양준석 코드.
- 측정 스크립트는 저장소에 넣지 않았다(데이터 4천 행을 넣어 테스트 시간이 늘어남). 같은 측정이 필요하면 이 문서의 §2·§3 방법대로 다시 돌린다.
