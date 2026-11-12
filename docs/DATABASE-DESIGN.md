# 데이터베이스 설계 (DATABASE-DESIGN.md)

> 프로젝트: 동잇(Doing_It) — 팀 협업 프로젝트 관리 시스템
> DB: MariaDB 10.11 LTS(Docker) | ORM: SQLAlchemy 2.x · Alembic · PyMySQL | 담당: 백엔드 B
> 버전: v0.6 (DATABASE.md v0.5 + 구현 설계 초안 통합: 단계별 마이그레이션, P2 컬럼 분리, `users` 참조 FK RESTRICT, `login_id` 소문자 강제, 이력 행 CHECK, 정렬 기준 통일, OWNER 행 잠금) · v0.5 (users.deleted_at(P2 탈퇴), 댓글 300자, 체크리스트 업무당 10개) · v0.4 (이름·제목 30자, 체크리스트(P2)) · v0.3 (email → login_id)
> 근거: PROPOSAL → CONSTITUTION §4·§6·§8 → REQUIREMENTS v0.8 → API-SPEC v0.4. 문서끼리 다르면 앞쪽 문서를 따른다.

## 1. 설계 원칙

| # | 원칙 | 근거 |
| :-: | --- | --- |
| 1 | 스키마는 **Alembic 마이그레이션으로만** 바꾼다. DDL을 직접 실행하지 않는다 | CONSTITUTION 4-2 |
| 2 | 상태·역할은 Python `enum.Enum` + DB `VARCHAR` + `CHECK`. MariaDB `ENUM` 타입은 쓰지 않는다(값 추가 시 마이그레이션이 간단함) | CONSTITUTION 4-4 |
| 3 | 한 행으로 판단되는 규칙은 DB(UNIQUE·CHECK·FK)로, 여러 행에 걸친 규칙은 서비스 계층에서 막는다 | CONSTITUTION 8-4 |
| 4 | 업무 생성·변경·삭제와 이력 기록은 **한 트랜잭션** | CONSTITUTION 8-1·8-2 |
| 5 | 삭제는 실제 삭제(CASCADE). 업무가 지워져도 이력은 `task_id = NULL`로 남긴다 | CONSTITUTION 8-3 |
| 6 | 시각은 UTC로 저장하고 응답은 ISO 8601 `Z`. 화면에서 한국 시간으로 바꾼다 | CONSTITUTION 8-5 |
| 7 | `InnoDB` · `utf8mb4` · `utf8mb4_unicode_ci`(예외: `login_id`, §4.1). PostgreSQL 전용 문법(`FILTER` 등) 금지 | CLAUDE.md §5 |
| 8 | **지금 쓰지 않는 컬럼·테이블은 만들지 않는다.** P1·P2용은 해당 단계 마이그레이션에서 추가한다 | CLAUDE.md §5 |

## 2. 마이그레이션 단계

| 리비전 | 시점 | 내용 | 기능 ID |
| --- | --- | --- | --- |
| `0001_p0_initial` | 스프린트 1 첫날 | `users`, `projects`, `project_members`, `tasks`, `task_activities` | AUTH-01~04, PRJ-01~05·07, TASK-01~06, LOG-01·02 |
| `0002_p1_comments` | P0 게이트(11/19) 이후 | `task_comments` | CMT-01·02 |
| `0003_p2_*` | P1 완료 후, 기능마다 1개 | `task_checklist_items`, `users.deleted_at`, `projects.is_archived`, `tasks.position` | TASK-08·09·10, AUTH-08, 보관 |

- **P0 테이블 5개를 스프린트 1 첫 리비전에 모두 만든다.** 멤버 제거(PRJ-05)가 스프린트 1에 있고, 제거할 때 담당 업무를 해제하고 이력을 남겨야 하므로 `tasks`·`task_activities`가 처음부터 필요하다.
- 리비전은 백엔드 B만 만들고, 다른 사람은 `alembic upgrade head`만 실행한다. PR 전에 `alembic heads`가 1개인지 확인한다(브랜치마다 리비전을 만들면 head가 갈라진다).

## 3. ERD

P0 테이블은 실선 관계로, P1·P2 테이블·컬럼은 이름 옆에 단계를 적는다.

```mermaid
erDiagram
    USERS ||--o{ PROJECT_MEMBERS : "참여"
    PROJECTS ||--o{ PROJECT_MEMBERS : "멤버"
    USERS ||--o{ PROJECTS : "생성 created_by"
    PROJECTS ||--o{ TASKS : "포함"
    USERS ||--o{ TASKS : "작성 created_by"
    USERS |o--o{ TASKS : "담당 assignee_id"
    PROJECTS ||--o{ TASK_ACTIVITIES : "이력"
    TASKS |o--o{ TASK_ACTIVITIES : "이력 (삭제 후 NULL)"
    USERS ||--o{ TASK_ACTIVITIES : "변경자"
    TASKS ||--o{ TASK_COMMENTS : "댓글 (P1)"
    USERS ||--o{ TASK_COMMENTS : "작성 (P1)"
    TASKS ||--o{ TASK_CHECKLIST_ITEMS : "체크리스트 (P2)"

    USERS {
        bigint id PK
        varchar login_id UK "a-z0-9 4~20, bin"
        varchar password_hash
        varchar name "1~50"
        varchar system_role "ADMIN | USER"
        tinyint is_active
        datetime deleted_at "P2, NULL"
        datetime created_at
        datetime updated_at
    }
    PROJECTS {
        bigint id PK
        varchar name "1~30"
        text description
        date start_date
        date end_date
        tinyint is_archived "P2"
        bigint created_by FK
        datetime created_at
        datetime updated_at
    }
    PROJECT_MEMBERS {
        bigint id PK
        bigint project_id FK
        bigint user_id FK
        varchar role "OWNER | MEMBER"
        datetime joined_at
    }
    TASKS {
        bigint id PK
        bigint project_id FK
        varchar title "1~30"
        text description
        varchar status "TODO | IN_PROGRESS | DONE"
        varchar priority "LOW | MEDIUM | HIGH | URGENT"
        bigint assignee_id FK "NULL"
        bigint created_by FK
        date due_date "NULL"
        int position "P2"
        datetime completed_at "DONE일 때만"
        datetime created_at
        datetime updated_at
    }
    TASK_ACTIVITIES {
        bigint id PK
        bigint task_id FK "NULL"
        bigint project_id FK
        bigint user_id FK
        varchar action "CREATED | UPDATED | DELETED"
        varchar field "NULL"
        varchar old_value "NULL"
        varchar new_value "NULL"
        datetime created_at
    }
    TASK_COMMENTS {
        bigint id PK
        bigint task_id FK
        bigint user_id FK
        varchar content "1~300"
        datetime created_at
        datetime updated_at
    }
    TASK_CHECKLIST_ITEMS {
        bigint id PK
        bigint task_id FK
        varchar content "1~100"
        tinyint is_done
        int position
        datetime created_at
        datetime updated_at
    }
```

### 관계 요약

| 관계 | 유형 | 설명 |
| --- | --- | --- |
| Users ↔ Projects | 다대다 | `project_members`로 연결하고 역할(role)을 함께 저장 |
| Projects → Tasks | 일대다 | 프로젝트 삭제 시 업무도 삭제 |
| Users → Tasks (담당) | 일대다, 선택 | 담당자가 없을 수 있음 |
| Tasks → TaskActivities | 일대다 | 업무가 삭제돼도 이력은 `task_id = NULL`로 유지 |
| Tasks → TaskComments (P1) | 일대다 | 업무 삭제 시 댓글도 삭제 |
| Tasks → TaskChecklistItems (P2) | 일대다 | 업무 삭제 시 항목도 삭제 |

## 4. 테이블 정의

공통 규칙:
- PK는 `BIGINT AUTO_INCREMENT`.
- `created_at`·`updated_at`은 `DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`. `updated_at`은 SQLAlchemy `onupdate=func.now()`로 갱신한다.
- CHECK 제약 SQL은 Alembic 리비전에 그대로 옮긴다. 제약 이름은 §10 규칙을 따른다.

### 4.1 users (P0)

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | |
| login_id | VARCHAR(20) **COLLATE utf8mb4_bin** | N | | `uq_users_login_id`, `ck_users_login_id_format` | 로그인 아이디. 멤버 추가 시 검색 키 |
| password_hash | VARCHAR(255) | N | | | bcrypt. 어떤 응답에도 넣지 않음 |
| name | VARCHAR(50) | N | | `ck_users_name_not_blank` | 표시 이름 1~50자 |
| system_role | VARCHAR(10) | N | `'USER'` | `ck_users_system_role` | 가입 시 항상 `USER`. `ADMIN`은 P2(ADM-01) |
| is_active | TINYINT(1) | N | `1` | | 0이면 403 `ACCOUNT_DISABLED` |
| created_at / updated_at | DATETIME | N | now | | |

```sql
CONSTRAINT ck_users_login_id_format CHECK (login_id REGEXP '^[a-z0-9]{4,20}$')
CONSTRAINT ck_users_system_role     CHECK (system_role IN ('ADMIN','USER'))
CONSTRAINT ck_users_name_not_blank  CHECK (CHAR_LENGTH(TRIM(name)) > 0)
```

**아이디는 소문자만 저장된다.**
- 앱(Pydantic)이 입력한 대문자를 소문자로 바꾼 뒤 저장한다(AUTH-01).
- DB는 `utf8mb4_bin` 콜레이션 + REGEXP CHECK로 대문자가 들어오는 것을 막는다. 기본 `_ci` 콜레이션에서는 REGEXP가 대소문자를 구분하지 않아 `'MinHo'`도 통과하므로 이 컬럼만 `_bin`으로 둔다.
- 로그인·멤버 추가 때도 입력을 소문자로 바꿔 조회한다. 그래서 대소문자만 다른 아이디도 같은 아이디로 보고 409로 막는다.

**P2 추가 컬럼 (AUTH-08 회원 탈퇴)**

| 컬럼 | 타입 | NULL | 설명 |
| --- | --- | :-: | --- |
| deleted_at | DATETIME | Y | 탈퇴 시각. 값이 있으면 탈퇴한 사용자. 행은 지우지 않고 `name`을 "탈퇴한 사용자"로, `is_active`를 0으로 바꾼다. `login_id`는 남겨 재사용을 막는다 |

### 4.2 projects (P0)

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | |
| name | VARCHAR(30) | N | | `ck_projects_name_not_blank` | 앞뒤 공백 제거 후 1~30자 (PRJ-01). 한글도 1자 |
| description | TEXT | Y | | | |
| start_date | DATE | Y | | | |
| end_date | DATE | Y | | `ck_projects_period` | |
| created_by | BIGINT | N | | FK → users.id `RESTRICT` | |
| created_at / updated_at | DATETIME | N | now | | |

```sql
CONSTRAINT ck_projects_name_not_blank CHECK (CHAR_LENGTH(TRIM(name)) > 0)
CONSTRAINT ck_projects_period         CHECK (start_date IS NULL OR end_date IS NULL OR end_date >= start_date)
```

**P2 추가 컬럼:** `is_archived TINYINT(1) NOT NULL DEFAULT 0` — 프로젝트 보관. P0·P1을 모두 마친 뒤에만 쓴다(CONSTITUTION 8-3).

### 4.3 project_members (P0)

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | |
| project_id | BIGINT | N | | FK → projects.id `CASCADE` | |
| user_id | BIGINT | N | | FK → users.id `RESTRICT` | |
| role | VARCHAR(10) | N | | `ck_project_members_role` | `OWNER` \| `MEMBER`. VIEWER는 보류(CONSTITUTION 6-3) |
| joined_at | DATETIME | N | now | | |

```sql
CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id)   -- 409 ALREADY_MEMBER
CONSTRAINT ck_project_members_role         CHECK (role IN ('OWNER','MEMBER'))
```

- "OWNER 최소 1명"은 여러 행에 걸친 규칙이라 서비스 계층에서 검사한다(400 `LAST_OWNER`). 동시 제거는 §6.1의 잠금으로 막는다.

### 4.4 tasks (P0)

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | |
| project_id | BIGINT | N | | FK → projects.id `CASCADE` | |
| title | VARCHAR(30) | N | | `ck_tasks_title_not_blank` | 1~30자 (TASK-01) |
| description | TEXT | Y | | | |
| status | VARCHAR(20) | N | `'TODO'` | `ck_tasks_status` | 생성은 항상 `TODO`(API는 status를 받지 않음) |
| priority | VARCHAR(10) | N | `'MEDIUM'` | `ck_tasks_priority` | |
| assignee_id | BIGINT | Y | | FK → users.id `SET NULL` | 프로젝트 멤버인지는 서비스 계층에서 검사 (TASK-03) |
| created_by | BIGINT | N | | FK → users.id `RESTRICT` | 수정·삭제 권한 판단 (TASK-06) |
| due_date | DATE | Y | | | 과거 날짜·프로젝트 기간 밖 날짜도 허용 |
| completed_at | DATETIME | Y | | `ck_tasks_completed_at` | `DONE`이 될 때 기록, 다른 상태로 바뀌면 NULL |
| created_at / updated_at | DATETIME | N | now | | |

```sql
CONSTRAINT ck_tasks_title_not_blank CHECK (CHAR_LENGTH(TRIM(title)) > 0)
CONSTRAINT ck_tasks_status          CHECK (status IN ('TODO','IN_PROGRESS','DONE'))
CONSTRAINT ck_tasks_priority        CHECK (priority IN ('LOW','MEDIUM','HIGH','URGENT'))
CONSTRAINT ck_tasks_completed_at    CHECK ((status = 'DONE') = (completed_at IS NOT NULL))
```

**P2 추가 컬럼:** `position INT NOT NULL DEFAULT 0` — 드래그 앤 드롭(TASK-08)용 컬럼 안 순서. 추가해도 칸반 기본 정렬(§7)은 바꾸지 않는다. 바꾸려면 REQUIREMENTS TASK-05를 먼저 고친다.

### 4.5 task_activities — 변경 이력 (P0)

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | 같은 초 안의 순서 보조 |
| task_id | BIGINT | Y | | FK → tasks.id `SET NULL` | 업무 삭제 후에도 이력 유지 |
| project_id | BIGINT | N | | FK → projects.id `CASCADE` | 프로젝트별 최근 이력 조회용. 프로젝트 삭제 시 함께 삭제 |
| user_id | BIGINT | N | | FK → users.id `RESTRICT` | 변경한 사람 |
| action | VARCHAR(10) | N | | `ck_task_activities_action` | |
| field | VARCHAR(20) | Y | | `ck_task_activities_field` | |
| old_value | VARCHAR(255) | Y | | | 문자열. NULL은 "없음" |
| new_value | VARCHAR(255) | Y | | | |
| created_at | DATETIME | N | now | | 이력 행은 UPDATE하지 않는다 |

```sql
CONSTRAINT ck_task_activities_action CHECK (action IN ('CREATED','UPDATED','DELETED'))
CONSTRAINT ck_task_activities_field  CHECK (
  (action = 'UPDATED' AND field IN ('status','assignee_id','due_date','priority'))
  OR (action IN ('CREATED','DELETED') AND field IS NULL)
)
```

행 모양 (LOG-01·02, API-SPEC §5.3·§5.4):

| 동작 | action | field | old_value | new_value |
| --- | --- | --- | --- | --- |
| 업무 생성 | `CREATED` | NULL | NULL | NULL |
| 상태 변경 | `UPDATED` | `status` | `TODO` | `IN_PROGRESS` |
| 담당자 변경 | `UPDATED` | `assignee_id` | `"2"` 또는 NULL | `"3"` 또는 NULL |
| 마감일 변경 | `UPDATED` | `due_date` | `2026-11-20` | `2026-11-25` |
| 우선순위 변경 | `UPDATED` | `priority` | `MEDIUM` | `HIGH` |
| 업무 삭제 | `DELETED` | NULL | **삭제 전 제목** | NULL |
| 멤버 제거로 담당 해제 | `UPDATED` | `assignee_id` | `"3"` | NULL (변경자 = 제거한 OWNER) |

- 한 번의 수정에서 여러 항목이 바뀌면 항목마다 1행씩 기록한다. 같은 값으로 바꾸면 기록하지 않는다.
- 제목·설명 변경과 체크리스트 변경은 기록하지 않는다(LOG-01 범위).
- 담당자 값은 사용자 id 문자열로 저장한다. 조회 응답에서 이름으로 바꾸는 방법은 API-SPEC §6을 따른다(§12).

### 4.6 task_comments — 댓글 (P1, `0002`)

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | |
| task_id | BIGINT | N | | FK → tasks.id `CASCADE` | |
| user_id | BIGINT | N | | FK → users.id `RESTRICT` | 작성자. 본인만 수정·삭제 (CMT-02) |
| content | VARCHAR(300) | N | | `ck_task_comments_content_not_blank` | 앞뒤 공백 제거 후 1~300자 (CMT-01) |
| created_at / updated_at | DATETIME | N | now | | |

```sql
CONSTRAINT ck_task_comments_content_not_blank CHECK (CHAR_LENGTH(TRIM(content)) > 0)
```

### 4.7 task_checklist_items — 업무 체크리스트 (P2, `0003`)

TASK-09·10용.

| 컬럼 | 타입 | NULL | 기본값 | 제약 | 설명 |
| --- | --- | :-: | --- | --- | --- |
| id | BIGINT | N | AI | PK | |
| task_id | BIGINT | N | | FK → tasks.id `CASCADE` | |
| content | VARCHAR(100) | N | | `ck_task_checklist_items_content_not_blank` | 1~100자 |
| is_done | TINYINT(1) | N | `0` | | 완료 체크 |
| position | INT | N | `0` | | 업무 안에서 항목 순서 |
| created_at / updated_at | DATETIME | N | now | | |

- 접근 권한은 상위 업무의 프로젝트 멤버십으로 검사한다.
- **업무당 최대 10개**는 서비스 계층에서 검사한다(`CHECKLIST_LIMIT_EXCEEDED`). 동시에 추가해 11개가 되지 않도록 §6.1과 같은 방식으로 상위 `tasks` 행을 먼저 잠근다.

## 5. FK 삭제 동작

| FK | 동작 | 이유 |
| --- | --- | --- |
| project_members.project_id | CASCADE | 프로젝트 삭제 시 멤버십도 삭제 |
| tasks.project_id | CASCADE | 프로젝트 삭제 시 업무도 삭제 (PRJ-03) |
| task_activities.project_id | CASCADE | 프로젝트 삭제 시 이력도 삭제 (API-SPEC DELETE /projects) |
| task_activities.task_id | **SET NULL** | 업무 삭제 후에도 이력 유지 (CONSTITUTION 8-3) |
| task_comments.task_id (P1) | CASCADE | 업무 삭제 시 댓글도 삭제 |
| task_checklist_items.task_id (P2) | CASCADE | 업무 삭제 시 항목도 삭제 |
| tasks.assignee_id | SET NULL | 안전장치. 실제 담당 해제는 서비스가 이력과 함께 처리 |
| 그 외 `users` 참조 (`created_by`, `user_id`) | **RESTRICT** | 사용자 행은 지우지 않는다(탈퇴도 `deleted_at`). 실수로 지우면 이력이 연쇄 삭제되지 않고 오류가 나야 한다 |

> 프로젝트를 삭제하면 `task_activities` 행에 두 경로(`project_id` CASCADE, `tasks` 경유 SET NULL)가 함께 걸린다. InnoDB는 이를 허용하지만 pytest에 "업무·이력이 있는 프로젝트 삭제" 케이스를 넣어 확인한다(§9).

## 6. 트랜잭션 단위

서비스 함수 하나가 트랜잭션 하나다. 중간에 실패하면 전체를 롤백한다.

| # | 동작 | 한 트랜잭션 안에서 하는 일 | API |
| :-: | --- | --- | --- |
| 1 | 프로젝트 생성 | `projects` INSERT → `project_members(role=OWNER)` INSERT | POST /projects |
| 2 | 업무 생성 | `tasks` INSERT → `task_activities(CREATED)` INSERT | POST /projects/{id}/tasks |
| 3 | 업무 수정 | 대상 `tasks` 행 조회 → 권한 검사 → 바뀐 필드 UPDATE(`DONE`이면 `completed_at` 처리) → 바뀐 이력 필드마다 `task_activities` INSERT | PATCH /tasks/{id} |
| 4 | 업무 삭제 | `task_activities(DELETED, old_value=제목)` INSERT → `tasks` DELETE | DELETE /tasks/{id} |
| 5 | 멤버 제거 | **OWNER 행 잠금(§6.1)** → OWNER 수 확인 → 대상이 담당한 이 프로젝트 업무마다 `assignee_id=NULL` + 이력 INSERT → `project_members` DELETE | DELETE /projects/{id}/members/{user_id} |
| 6 | 프로젝트 삭제 | `projects` DELETE (나머지는 CASCADE) | DELETE /projects/{id} |

### 6.1 OWNER 동시 제거 막기

OWNER 2명이 동시에 서로를 제거하면, 둘 다 "OWNER가 2명"을 확인하고 통과해 OWNER가 0명이 될 수 있다. 멤버 제거(P2의 역할 변경 PRJ-08, 프로젝트 나가기 PRJ-09 포함)는 OWNER 수를 세기 전에 **그 프로젝트의 OWNER 행을 모두 잠근다.**

```sql
SELECT id FROM project_members
WHERE project_id = :project_id AND role = 'OWNER'
FOR UPDATE;
```

- 먼저 잠근 요청이 끝날 때까지 두 번째 요청은 기다린다. 두 번째 요청은 OWNER가 1명인 상태를 보고 400 `LAST_OWNER`로 거절된다.
- SQLAlchemy: `select(ProjectMember).where(...).with_for_update()`.
- pytest: 두 스레드가 서로를 동시에 제거 → 하나만 204, 나머지는 400, OWNER 1명 남음.

## 7. 정렬 기준 (통일)

API-SPEC과 REQUIREMENTS에 적힌 정렬을 그대로 쿼리로 옮긴다. **모든 목록은 마지막에 `id`를 붙여** 같은 값끼리의 순서를 고정한다(페이지가 바뀌어도 항목이 중복·누락되지 않음).

| 목록 | 정렬 | 근거 |
| --- | --- | --- |
| 내 프로젝트 | `created_at DESC, id DESC` | API-SPEC GET /projects |
| 멤버 | OWNER 먼저 → `joined_at` → `id` | API-SPEC GET /members |
| 칸반 컬럼 | 우선순위 높은 순(`URGENT → HIGH → MEDIUM → LOW`) → 마감일 빠른 순(없음은 뒤) → `id` | TASK-05, API-SPEC GET /tasks |
| 마감 임박·지연 (P1) | 마감일 빠른 순 → `id` | API-SPEC DASH-03 |
| 내 업무 (P1) | 지연 → 임박 → 나머지, 그룹 안에서 마감일 빠른 순(없음은 뒤) → `id` | API-SPEC DASH-04 |
| 업무 이력·최근 이력 (P1) | `created_at DESC, id DESC` | API-SPEC LOG-03 |
| 댓글 (P1) | `created_at, id` | API-SPEC 댓글 |
| 체크리스트 (P2) | `position, id` | API-SPEC 체크리스트 |

> **우선순위 함정:** `priority`는 문자열이라 그냥 정렬하면 알파벳순(`HIGH → LOW → MEDIUM → URGENT`)이 된다. 반드시 `FIELD(priority, 'URGENT','HIGH','MEDIUM','LOW')`(SQLAlchemy `case()`)로 순서를 준다. 정렬용 식은 `backend/app/models/enums.py`에 한 번만 정의하고 모든 쿼리가 가져다 쓴다.

## 8. 인덱스와 주요 쿼리

### 8.1 인덱스

| 단계 | 테이블 | 이름 | 컬럼 | 쓰는 곳 |
| --- | --- | --- | --- | --- |
| P0 | users | `uq_users_login_id` | (login_id) | 로그인, 멤버 추가 |
| P0 | project_members | `uq_project_members_project_user` | (project_id, user_id) | 멤버십 확인(모든 요청의 `require_project_role`) |
| P0 | project_members | `ix_project_members_user_id` | (user_id) | 내 프로젝트 목록 |
| P0 | tasks | `ix_tasks_project_status` | (project_id, status) | 칸반 컬럼 |
| P0 | tasks | `ix_tasks_assignee_status` | (assignee_id, status) | 멤버 제거 시 담당 업무 찾기, P1 내 업무·담당자별 현황 |
| P1 | tasks | `ix_tasks_project_due` | (project_id, due_date) | 마감 임박·지연 |
| P0 | task_activities | `ix_task_activities_task` | (task_id, created_at, id) | P1 업무 이력 |
| P0 | task_activities | `ix_task_activities_project` | (project_id, created_at, id) | P1 최근 이력 20건 |
| P1 | task_comments | `ix_task_comments_task` | (task_id, created_at) | 댓글 목록 |
| P2 | task_checklist_items | `ix_task_checklist_items_task` | (task_id, position) | 체크리스트 |

- FK 컬럼에는 InnoDB가 인덱스를 자동으로 만든다. 위 복합 인덱스의 앞쪽 컬럼과 겹치면 따로 만들지 않는다.
- `task_activities` 인덱스는 FK 때문에 어차피 필요하므로 P0 리비전에서 복합 인덱스로 만든다.
- 칸반 정렬(우선순위·마감일)은 인덱스로 처리하지 않는다. 한 컬럼에 업무가 수십 개 수준이라 메모리 정렬로 충분하다.

### 8.2 P0 쿼리

**멤버십 확인 (`require_project_role`)**
```sql
SELECT role FROM project_members
WHERE project_id = :project_id AND user_id = :user_id;
-- 프로젝트가 없으면 먼저 404, 행이 없으면 403 NOT_PROJECT_MEMBER
```

**내 프로젝트 목록 (PRJ-02)**
```sql
SELECT p.*, pm.role AS my_role
FROM projects p
JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :me
ORDER BY p.created_at DESC, p.id DESC
LIMIT :size OFFSET :offset;
```

**칸반 컬럼 (TASK-05)** — 컬럼마다 1번씩 호출
```sql
SELECT * FROM tasks
WHERE project_id = :project_id AND status = :status
ORDER BY FIELD(priority, 'URGENT', 'HIGH', 'MEDIUM', 'LOW'),
         due_date IS NULL, due_date, id
LIMIT :size OFFSET :offset;
```

**멤버 목록 (PRJ-07)**
```sql
SELECT u.id AS user_id, u.login_id, u.name, pm.role, pm.joined_at
FROM project_members pm
JOIN users u ON u.id = pm.user_id
WHERE pm.project_id = :project_id
ORDER BY pm.role = 'OWNER' DESC, pm.joined_at, pm.id;
```

### 8.3 P1·P2 쿼리

`:today`는 앱에서 넘긴다. DB 세션이 UTC라 `CURRENT_DATE`를 쓰면 한국 시간 오전 9시 전에 하루가 어긋난다(기준은 한국 날짜, API-SPEC §1.6).

**프로젝트 진행률 (DASH-01)** — 업무가 없으면 0%
```sql
SELECT p.id,
       COUNT(t.id)                                       AS total,
       COALESCE(SUM(t.status = 'DONE'), 0)               AS done,
       COALESCE(ROUND(100 * SUM(t.status = 'DONE')
                / NULLIF(COUNT(t.id), 0)), 0)            AS percent
FROM projects p
LEFT JOIN tasks t ON t.project_id = p.id
WHERE p.id = :project_id
GROUP BY p.id;
```

**담당자별 상태별 업무 수 (DASH-02)** — 담당자 없음(`assignee_id IS NULL`)도 한 줄로 포함
```sql
SELECT t.assignee_id, u.login_id, u.name,
       SUM(t.status = 'TODO')        AS todo,
       SUM(t.status = 'IN_PROGRESS') AS in_progress,
       SUM(t.status = 'DONE')        AS done
FROM tasks t
LEFT JOIN users u ON u.id = t.assignee_id
WHERE t.project_id = :project_id
GROUP BY t.assignee_id, u.login_id, u.name;
```

**마감 임박·지연 (DASH-03)** — 마감일이 오늘이면 임박
```sql
SELECT *,
       CASE WHEN due_date < :today THEN 'OVERDUE' ELSE 'DUE_SOON' END AS alert
FROM tasks
WHERE project_id = :project_id
  AND status <> 'DONE'
  AND due_date IS NOT NULL
  AND due_date <= :today + INTERVAL 3 DAY
ORDER BY due_date, id;
```

**내 업무 (DASH-04)**
```sql
SELECT t.*, p.name AS project_name,
       CASE WHEN t.due_date < :today THEN 'OVERDUE'
            WHEN t.due_date <= :today + INTERVAL 3 DAY THEN 'DUE_SOON' END AS alert
FROM tasks t
JOIN projects p ON p.id = t.project_id
WHERE t.assignee_id = :me AND t.status <> 'DONE'
ORDER BY CASE WHEN t.due_date < :today THEN 0
              WHEN t.due_date <= :today + INTERVAL 3 DAY THEN 1
              ELSE 2 END,
         t.due_date IS NULL, t.due_date, t.id
LIMIT :size OFFSET :offset;
```

**업무 진행률 (TASK-10, P2)** — 항목이 없는 업무는 결과에 나오지 않으며 화면에 표시하지 않는다
```sql
SELECT task_id,
       COUNT(*)                                  AS total,
       SUM(is_done = 1)                          AS done,
       ROUND(100 * SUM(is_done = 1) / COUNT(*))  AS percent
FROM task_checklist_items
WHERE task_id IN (:task_ids)
GROUP BY task_id;
```

## 9. DB 규칙 테스트 (pytest)

API-SPEC §10 필수 대상 중 DB와 직접 관련된 것.

| 규칙 | 테스트 |
| --- | --- |
| 아이디 소문자·중복 | `MinHo`로 가입 → `minho`로 저장 / 이미 있는 아이디를 대소문자만 바꿔 가입 → 409 / DB에 대문자 직접 INSERT → CHECK 오류 |
| 멤버 중복 | 같은 사람 두 번 추가 → 409 `ALREADY_MEMBER` |
| 제목 길이 | 31자 → 422, 공백만 → 422 |
| 이력 같은 트랜잭션 | 상태+담당자 동시 변경 → 이력 2행 / 이력 INSERT를 강제로 실패시키면 업무도 바뀌지 않음 |
| completed_at | DONE 전환 시 값 있음, 다른 상태로 바꾸면 NULL |
| 업무 삭제 | 삭제 후 이력 `task_id` NULL, `DELETED` 행의 `old_value` = 제목 |
| 멤버 제거 | 담당 업무 `assignee_id` NULL + 업무마다 이력 1행 |
| LAST_OWNER | 유일한 OWNER 제거 → 400, 데이터 변화 없음 |
| OWNER 동시 제거 | 두 OWNER가 서로를 동시에 제거 → 하나만 성공, OWNER 1명 남음 |
| 칸반 정렬 | URGENT·HIGH·MEDIUM·LOW와 마감 없음이 섞인 데이터 → TASK-05 순서대로 나옴 |
| 프로젝트 삭제 | 멤버·업무·이력 모두 삭제, 다른 프로젝트 데이터는 그대로 |

- 테스트 DB는 개발 DB와 분리한다(`.env`의 `TEST_DATABASE_URL`, 같은 MariaDB 컨테이너의 별도 스키마).
- SQLite로 대신하지 않는다. CHECK, `FIELD()`, 콜레이션, `FOR UPDATE` 동작이 다르다.

## 10. 구현 메모

- 접속 URL: `mysql+pymysql://USER:PASSWORD@localhost:3306/doing_it?charset=utf8mb4`. 값은 `.env`에 두고 저장소에는 `.env.example`만 올린다.
- 연결할 때마다 `SET time_zone = '+00:00'`을 실행한다(SQLAlchemy `connect` 이벤트). `DATETIME`은 시간대를 저장하지 않으므로 앱이 항상 UTC로 넣고, 응답에서 `Z`를 붙인다.
- MariaDB 10.2 이상부터 CHECK가 실제로 동작한다. 팀 전원이 10.11 LTS를 Docker로 쓴다.
- 조건부 개수는 `SUM(조건식)`으로 센다(참이면 1). PostgreSQL의 `FILTER`는 쓰지 않는다.
- 제약 이름은 SQLAlchemy `MetaData(naming_convention=...)`로 고정한다. 이름이 있어야 Alembic이 나중에 제약을 지우거나 바꿀 수 있다.
  ```python
  NAMING = {
      "ix": "ix_%(table_name)s_%(column_0_name)s",
      "uq": "uq_%(table_name)s_%(column_0_name)s",
      "ck": "ck_%(table_name)s_%(constraint_name)s",
      "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
      "pk": "pk_%(table_name)s",
  }
  ```
- Enum은 `backend/app/models/enums.py` 한곳에 둔다: `TaskStatus`, `TaskPriority`, `ProjectRole`, `SystemRole`, `ActivityAction`, `ActivityField`. 우선순위 정렬 식(§7)도 여기에 둔다.
- Alembic `autogenerate`는 CHECK 제약과 컬럼 콜레이션을 잡지 못한다. 리비전 파일에 직접 적고 리뷰 때 확인한다.
- 시드: `backend/scripts/seed.py`로 시연용 사용자 4명, 프로젝트 1개, 업무 12개 정도를 넣는다(상태·우선순위·마감 분포를 UI-DESIGN 화면과 비슷하게). 마이그레이션에는 넣지 않는다.

## 11. 이전 DATABASE.md v0.5에서 바뀐 점

| # | 항목 | v0.5 | v0.6 | 이유 |
| :-: | --- | --- | --- | --- |
| 1 | P2 컬럼 (`deleted_at`, `is_archived`, `position`) | P0 테이블에 포함 | P2 마이그레이션에서 추가 | 지금 쓰지 않는 컬럼 제외 |
| 2 | `task_comments` | 처음부터 포함 | P1 마이그레이션 | CMT는 P1 |
| 3 | 첫 마이그레이션 범위 | 정하지 않음 | P0 5개 테이블 모두 | 스프린트 1 멤버 제거가 업무·이력을 씀 |
| 4 | `users` 참조 FK | 일부 CASCADE (`project_members`, `task_comments`) | 모두 RESTRICT (assignee만 SET NULL) | 사용자 행은 지우지 않음. 실수 삭제 시 이력 연쇄 삭제 방지 |
| 5 | `login_id` | 기본 `_ci` 콜레이션 | `utf8mb4_bin` + CHECK | 소문자만 저장되도록 DB에서 강제 |
| 6 | 이력 행 규칙 | 설명만 | `ck_task_activities_field` + 행 모양 표 | API-SPEC §5.3·§5.4(삭제 시 제목, 멤버 제거 시 담당 해제) 반영 |
| 7 | `completed_at` | 설명만 | `ck_tasks_completed_at` | DB에서도 보장 |
| 8 | 공백만 있는 이름·제목·댓글 | 일부만 CHECK | `TRIM` CHECK로 통일 | 앱 검증이 빠져도 DB가 막음 |
| 9 | 정렬 | 칸반 인덱스가 `position` 기준 | §7 정렬표로 통일, 칸반 인덱스 `(project_id, status)` | 실제 정렬 기준(우선순위·마감일)과 맞춤 |
| 10 | DASH-02 쿼리 | `JOIN`이라 담당자 없음 누락 | `LEFT JOIN` + 상태별 열 | API-SPEC 응답(`assignee: null` 행)과 맞춤 |
| 11 | 동시성 | 체크리스트만 잠금 | OWNER 제거에도 `FOR UPDATE` | OWNER 0명 방지 |
| 12 | DB 이름 | `Doing_It` | `doing_it` | Linux 컨테이너에서 대소문자 혼동 방지 |

## 12. 확정된 결정 (2026-11-12)

| # | 항목 | 결정 | 근거 |
| :-: | --- | --- | --- |
| 1 | 담당자 이력 값 | 사용자 id 문자열 저장. API가 `users`를 조회해 `old_assignee`·`new_assignee`로 이름까지 돌려준다. 사용자 행은 지우지 않으므로 제거된 멤버도 이름이 나온다 | API-SPEC §6 |
| 2 | "오늘" 기준 | 한국 날짜(UTC+9 고정)를 앱에서 계산해 `:today`로 전달 | API-SPEC §1.6 |
