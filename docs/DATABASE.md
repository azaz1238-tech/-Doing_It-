# 데이터베이스 설계 (DATABASE.md)

> 프로젝트: 팀 협업 프로젝트 관리 시스템 (TeamBoard) | DB: MariaDB 10.11 | ORM: SQLAlchemy 2.x + Alembic + PyMySQL
> 버전: v0.2 (MariaDB 전환, 프로젝트 역할 2단계) | 관련 문서: [REQUIREMENTS.md](./REQUIREMENTS.md)

## 1. ERD

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : "생성(created_by)"
    USERS ||--o{ PROJECT_MEMBERS : "참여"
    PROJECTS ||--o{ PROJECT_MEMBERS : "멤버 보유"
    PROJECTS ||--o{ TASKS : "포함"
    USERS ||--o{ TASKS : "작성(created_by)"
    USERS |o--o{ TASKS : "담당(assignee_id)"
    TASKS ||--o{ TASK_COMMENTS : "댓글"
    USERS ||--o{ TASK_COMMENTS : "작성"
    TASKS ||--o{ TASK_ACTIVITIES : "변경 이력"
    USERS ||--o{ TASK_ACTIVITIES : "변경자"

    USERS {
        bigint id PK
        varchar email UK
        varchar password_hash
        varchar name
        varchar system_role "ADMIN | USER"
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    PROJECTS {
        bigint id PK
        varchar name
        text description
        date start_date
        date end_date
        boolean is_archived
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
        varchar title
        text description
        varchar status "TODO | IN_PROGRESS | DONE"
        varchar priority "LOW | MEDIUM | HIGH | URGENT"
        bigint assignee_id FK "nullable"
        bigint created_by FK
        date due_date "nullable"
        int position "컬럼 내 정렬"
        datetime completed_at "nullable"
        datetime created_at
        datetime updated_at
    }
    TASK_COMMENTS {
        bigint id PK
        bigint task_id FK
        bigint user_id FK
        text content
        datetime created_at
        datetime updated_at
    }
    TASK_ACTIVITIES {
        bigint id PK
        bigint task_id FK "nullable"
        bigint project_id FK
        bigint user_id FK
        varchar action "CREATED | UPDATED | DELETED"
        varchar field "nullable"
        varchar old_value "nullable"
        varchar new_value "nullable"
        datetime created_at
    }
```

## 2. 관계 요약

| 관계 | 유형 | 설명 |
| --- | --- | --- |
| Users ↔ Projects | 다대다 | `project_members`를 통해 연결하며, 역할(role)을 함께 저장 |
| Projects → Tasks | 일대다 | 프로젝트 삭제 시 업무도 삭제(CASCADE) |
| Users → Tasks (담당) | 일대다, 선택 | 담당자가 없을 수 있음. 사용자 삭제 시 NULL |
| Tasks → TaskComments | 일대다 | 업무 삭제 시 댓글도 삭제 |
| Tasks → TaskActivities | 일대다 | 업무가 삭제되어도 이력은 남기도록 `task_id`를 NULL 처리 |

## 3. 테이블 상세

### 3.1 users

| 컬럼 | 타입 | 제약조건 | 설명 |
| --- | --- | --- | --- |
| id | BIGINT AUTO_INCREMENT | PK | |
| email | VARCHAR(255) | NOT NULL, UNIQUE | 로그인 ID. 소문자로 저장 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 해시 |
| name | VARCHAR(50) | NOT NULL | 표시 이름 |
| system_role | VARCHAR(10) | NOT NULL, DEFAULT 'USER', CHECK IN ('ADMIN','USER') | |
| is_active | TINYINT(1) | NOT NULL, DEFAULT 1 | 비활성 계정은 로그인 불가 |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |
| updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### 3.2 projects

| 컬럼 | 타입 | 제약조건 | 설명 |
| --- | --- | --- | --- |
| id | BIGINT AUTO_INCREMENT | PK | |
| name | VARCHAR(100) | NOT NULL | |
| description | TEXT | NULL | |
| start_date | DATE | NULL | |
| end_date | DATE | NULL, CHECK (end_date >= start_date) | |
| is_archived | TINYINT(1) | NOT NULL, DEFAULT 0 | |
| created_by | BIGINT | NOT NULL, FK → users.id | |
| created_at / updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### 3.3 project_members

| 컬럼 | 타입 | 제약조건 | 설명 |
| --- | --- | --- | --- |
| id | BIGINT AUTO_INCREMENT | PK | |
| project_id | BIGINT | NOT NULL, FK → projects.id ON DELETE CASCADE | |
| user_id | BIGINT | NOT NULL, FK → users.id ON DELETE CASCADE | |
| role | VARCHAR(10) | NOT NULL, CHECK IN ('OWNER','MEMBER') | VIEWER는 추후 검토 (CONSTITUTION 6-3) |
| joined_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

- **UNIQUE (project_id, user_id)**: 같은 사람을 두 번 추가할 수 없음
- "OWNER 최소 1명" 규칙은 DB 제약 대신 서비스 계층에서 검사(LAST_OWNER 오류)

### 3.4 tasks

| 컬럼 | 타입 | 제약조건 | 설명 |
| --- | --- | --- | --- |
| id | BIGINT AUTO_INCREMENT | PK | |
| project_id | BIGINT | NOT NULL, FK → projects.id ON DELETE CASCADE | |
| title | VARCHAR(200) | NOT NULL | |
| description | TEXT | NULL | |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'TODO', CHECK IN ('TODO','IN_PROGRESS','DONE') | |
| priority | VARCHAR(10) | NOT NULL, DEFAULT 'MEDIUM', CHECK IN ('LOW','MEDIUM','HIGH','URGENT') | |
| assignee_id | BIGINT | NULL, FK → users.id ON DELETE SET NULL | 프로젝트 멤버인지는 서비스 계층에서 검사 |
| created_by | BIGINT | NOT NULL, FK → users.id | |
| due_date | DATE | NULL | |
| position | INTEGER | NOT NULL, DEFAULT 0 | 칸반 컬럼 안의 순서(드래그용, P2) |
| completed_at | DATETIME | NULL | DONE이 될 때 기록, 다른 상태로 바뀌면 NULL |
| created_at / updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### 3.5 task_comments

| 컬럼 | 타입 | 제약조건 | 설명 |
| --- | --- | --- | --- |
| id | BIGINT AUTO_INCREMENT | PK | |
| task_id | BIGINT | NOT NULL, FK → tasks.id ON DELETE CASCADE | |
| user_id | BIGINT | NOT NULL, FK → users.id ON DELETE CASCADE | |
| content | TEXT | NOT NULL, CHECK (CHAR_LENGTH(content) > 0) | |
| created_at / updated_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

### 3.6 task_activities (변경 이력)

| 컬럼 | 타입 | 제약조건 | 설명 |
| --- | --- | --- | --- |
| id | BIGINT AUTO_INCREMENT | PK | |
| task_id | BIGINT | NULL, FK → tasks.id ON DELETE SET NULL | 업무 삭제 후에도 이력 유지 |
| project_id | BIGINT | NOT NULL, FK → projects.id ON DELETE CASCADE | 프로젝트별 최근 이력 조회용 |
| user_id | BIGINT | NOT NULL, FK → users.id | 변경한 사람 |
| action | VARCHAR(10) | NOT NULL, CHECK IN ('CREATED','UPDATED','DELETED') | |
| field | VARCHAR(30) | NULL | 예: status, assignee_id, due_date |
| old_value | VARCHAR(255) | NULL | |
| new_value | VARCHAR(255) | NULL | |
| created_at | DATETIME | NOT NULL, DEFAULT CURRENT_TIMESTAMP | |

- 이력은 업무 수정과 **같은 트랜잭션**에서 기록한다. 수정이 실패하면 이력도 남지 않아야 한다.
- 한 번의 수정에서 여러 항목이 바뀌면 항목마다 1행씩 기록한다.

## 4. 인덱스

| 테이블 | 인덱스 | 용도 |
| --- | --- | --- |
| users | UNIQUE (email) | 로그인 조회 |
| project_members | UNIQUE (project_id, user_id) | 중복 방지, 멤버십 확인 |
| project_members | (user_id) | 내 프로젝트 목록 |
| tasks | (project_id, status, position) | 칸반 보드 조회 |
| tasks | (assignee_id, status) | 내 업무, 담당자별 현황 |
| tasks | (project_id, due_date) | 마감 임박·지연 조회 |
| task_comments | (task_id, created_at) | 댓글 목록 |
| task_activities | (task_id, created_at DESC) | 업무 이력 |
| task_activities | (project_id, created_at DESC) | 프로젝트 최근 이력 |

## 5. 주요 조회 쿼리

**프로젝트 진행률 (DASH-01)**
```sql
SELECT p.id,
       COUNT(t.id)                                        AS total,
       COALESCE(SUM(t.status = 'DONE'), 0)                AS done,
       COALESCE(ROUND(100 * SUM(t.status = 'DONE')
                / NULLIF(COUNT(t.id), 0)), 0)             AS progress
FROM projects p
LEFT JOIN tasks t ON t.project_id = p.id
WHERE p.id = :project_id
GROUP BY p.id;
```

**담당자별 상태별 업무 수 (DASH-02)**
```sql
SELECT u.id, u.name, t.status, COUNT(*) AS cnt
FROM tasks t
JOIN users u ON u.id = t.assignee_id
WHERE t.project_id = :project_id
GROUP BY u.id, u.name, t.status;
```

**마감 임박·지연 업무 (DASH-03)**
```sql
SELECT *,
       CASE WHEN due_date < CURRENT_DATE THEN 'OVERDUE' ELSE 'DUE_SOON' END AS alert
FROM tasks
WHERE project_id = :project_id
  AND status <> 'DONE'
  AND due_date IS NOT NULL
  AND due_date <= CURRENT_DATE + INTERVAL 3 DAY
ORDER BY due_date;
```

## 6. 구현 메모

- 상태·역할 값은 Python `enum.Enum`으로 정의하고, DB에는 VARCHAR + CHECK로 저장한다. (MariaDB ENUM 타입보다 Alembic 마이그레이션에서 값 추가가 간단함)
- MariaDB 10.2 이상부터 CHECK 제약이 실제로 동작한다. 팀 전원이 10.11 LTS를 Docker로 쓴다.
- 모든 테이블은 `ENGINE=InnoDB`, `CHARSET=utf8mb4`, `COLLATE=utf8mb4_unicode_ci`로 만든다. (한글·이모지 저장, FK·트랜잭션 지원)
- MariaDB `DATETIME`은 시간대 정보를 저장하지 않는다. 앱에서 항상 **UTC로 변환해 저장**하고, 응답에는 ISO 8601 형식(`Z` 포함)으로 내보내 화면에서 한국 시간으로 바꾼다. DB 세션도 `SET time_zone = '+00:00'`으로 맞춘다.
- `updated_at`은 SQLAlchemy `onupdate=func.now()`로 갱신한다.
- 접속 URL 예: `mysql+pymysql://user:password@localhost:3306/teamboard?charset=utf8mb4`
- MariaDB는 `SUM(조건식)`으로 조건부 개수를 셀 수 있다(참이면 1). PostgreSQL의 `FILTER` 구문은 쓰지 않는다.
- 초기 데이터: Alembic 이후 `seed.py`로 ADMIN 1명, 샘플 프로젝트 1개, 업무 10개 정도를 넣어 시연에 활용한다.
