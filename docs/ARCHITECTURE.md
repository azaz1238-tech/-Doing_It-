# 아키텍처 설계 (ARCHITECTURE.md)

> 프로젝트: 동잇(Doing_It) — 팀 협업 프로젝트 관리 시스템 | 버전: v0.1 (2026-11-12 결정 반영, §10) | 작성일: 2026-11-12
> 근거: PROPOSAL §5·§6 → CONSTITUTION §4~§9 → REQUIREMENTS v0.8 → API-SPEC v0.4 · DATABASE-DESIGN v0.6 · UI-DESIGN v0.2
> 이 문서는 **코드를 어디에, 어떤 규칙으로 둘지**를 정한다. 기능·API·테이블 정의는 위 문서를 따르고 여기서 다시 적지 않는다.

## 1. 전체 구조

```mermaid
flowchart LR
  B["브라우저<br/>localhost:5173"] -->|"화면 /projects ..."| V["Vite 개발 서버<br/>React"]
  B -->|"/api/* 요청"| V
  V -->|"프록시 /api → :8000"| F["FastAPI (Uvicorn)<br/>localhost:8000"]
  F -->|"PyMySQL · UTC 세션"| D[("MariaDB 10.11<br/>Docker :3306<br/>doing_it / doing_it_test")]
```

| 구성 | 실행 방법 | 포트 |
| --- | --- | --- |
| MariaDB | `docker compose up -d` (DB만 컨테이너) | 3306 |
| 백엔드 | `backend/.venv`에서 `uvicorn app.main:app --reload` | 8000 |
| 프론트 | `frontend`에서 `npm run dev` | 5173 |

- 브라우저는 항상 5173 하나만 본다. `/api`로 시작하는 요청만 Vite가 8000으로 넘기므로 개발 중에는 CORS 문제가 생기지 않는다(API-SPEC §1.1).
- **시연은 로컬에서 한다.** 클라우드 배포는 P2로 두고, 마무리 단계에 시간이 남을 때만 시도한다(§9).

## 2. 기술 스택 버전

| 영역 | 고정 값 | 비고 |
| --- | --- | --- |
| Python | **3.12** | 4명 모두 같은 버전. `backend/.python-version`에 적는다 |
| Node | **22 LTS** | `frontend/.nvmrc`에 `22`, `package.json`의 `engines`에도 적는다 |
| MariaDB | **10.11** | 이미지 `mariadb:10.11` |
| 백엔드 패키지 | FastAPI, Pydantic 2, Uvicorn, python-dotenv, SQLAlchemy 2.0, Alembic, PyMySQL, PyJWT, bcrypt / 개발: pytest, httpx, ruff, black | `requirements.txt`(실행)와 `requirements-dev.txt`(개발)에 `==`로 고정 |
| 프론트 패키지 | **React 19**, React Router, Axios, **Tailwind CSS 4**(`@tailwindcss/vite`) / 개발: Vite, ESLint, Prettier | `package-lock.json`을 커밋한다 |

- 정확한 패치 버전은 첫 세팅 PR에서 설치한 값을 그대로 고정하고, 스프린트 중에는 올리지 않는다.
- **이 목록 밖의 패키지는 추가하지 않는다**(CONSTITUTION 5-1). 아래는 자주 따라 들어오는데 쓰지 않는 것들이다.

| 쓰지 않는 패키지 | 이유 |
| --- | --- |
| `passlib` | `bcrypt`를 직접 쓴다. passlib는 최신 bcrypt와 호환 문제가 있다 |
| `python-multipart` | 로그인을 JSON으로 받으므로 form 처리가 필요 없다 |
| `tzdata` | "오늘"은 UTC+9 고정으로 계산한다(API-SPEC §1.6) |
| `cryptography` | MariaDB 기본 인증(`mysql_native_password`)에서는 PyMySQL이 필요로 하지 않는다 |
| `lucide-react`, 차트·상태관리·쿼리 라이브러리 | UI-DESIGN §9, 기술 스택에 없음 |

## 3. 저장소 구조

```
Doing_It/
├─ docs/                     명세 문서
├─ docker-compose.yml        MariaDB만
├─ docker/mariadb/init.sql   doing_it, doing_it_test 스키마 생성 (utf8mb4)
├─ .env.example              §6
├─ backend/
│  ├─ core/                  ★ 스타터킷 — 이 프로젝트 도메인을 모르는 코드만
│  ├─ app/                   동잇 도메인 코드
│  ├─ alembic/  alembic.ini
│  ├─ scripts/seed.py
│  └─ tests/
├─ frontend/
│  └─ src/
│     ├─ core/               ★ 스타터킷
│     └─ features/           동잇 화면·기능
└─ postman/                  Postman 컬렉션 (P0 외 API 확인용)
```

**스타터킷 규칙 (성공 기준 8):** `core/`는 `app/`·`features/`를 import하지 않는다. 반대 방향만 허용한다. 다른 프로젝트에 `core/`만 복사해도 동작해야 한다.

## 4. 백엔드

### 4.1 폴더

```
backend/
├─ core/
│  ├─ config.py        .env 읽기 (python-dotenv). 설정 객체 1개
│  ├─ db.py            engine, SessionLocal, get_db(), 연결 시 SET time_zone='+00:00'
│  ├─ security.py      bcrypt 해시·확인, JWT 발급·검증
│  ├─ auth.py          get_current_user 의존성 (Bearer 토큰 → 사용자)
│  ├─ exceptions.py    AppError, 예외 처리기(AppError·422 변환·404·500)
│  ├─ clock.py         get_today() — 한국 날짜 (테스트에서 교체 가능한 의존성)
│  └─ pagination.py    Page 쿼리 파라미터, { items, total, page, size } 응답
├─ app/
│  ├─ main.py          create_app(): 라우터를 prefix="/api"로 등록, CORS, 예외 처리기
│  ├─ routers/         auth.py · users.py · projects.py · members.py · tasks.py
│  │                   (P1: activities.py · comments.py · stats.py)
│  ├─ services/        auth_service · project_service · member_service · task_service
│  │                   activity_service(이력 기록) · permissions.py(require_project_role)
│  ├─ models/          base.py(naming convention) · enums.py · user · project · project_member · task · task_activity
│  └─ schemas/         요청·응답 Pydantic 모델 (common.py에 UTC 시각 직렬화)
└─ tests/              conftest.py · factories.py · test_auth · test_projects · test_members · test_tasks · test_permissions
```

### 4.2 계층별 책임

| 계층 | 하는 일 | 하지 않는 일 |
| --- | --- | --- |
| **router** | 경로·HTTP 메서드, 요청 스키마 검증, `Depends(get_current_user)`·`Depends(get_db)`, 서비스 호출, `response_model`·상태 코드 | DB 조회, 권한 판단, 업무 규칙 |
| **service** | 리소스 조회(없으면 404), `require_project_role`(403), 업무 규칙(400), DB 변경 + 이력 기록, **커밋** | HTTP 객체(`Request`, `Response`) 다루기, 응답 모양 만들기 |
| **model** | 테이블·컬럼·제약·관계 정의 | 로직 |
| **schema** | 입력 검증(공백 제거, 길이, 소문자 변환), 응답 필드 선택 | DB 접근 |

- 엔드포인트는 **`async def`가 아니라 `def`** 로 쓴다. PyMySQL·SQLAlchemy 세션은 동기 방식이라 `async def` 안에서 쓰면 서버 전체가 멈춘다. `def`로 쓰면 FastAPI가 스레드에서 실행한다.
- 응답 스키마에는 `password_hash`·`is_active` 필드를 아예 만들지 않는다(API-SPEC §4).

### 4.3 트랜잭션

- `get_db()`는 요청마다 세션 1개를 열고, 예외가 나면 `rollback`, 끝나면 `close`한다. **커밋하지 않는다.**
- **쓰기 서비스 함수가 마지막에 한 번 `db.commit()`** 한다. 서비스 함수 하나 = 트랜잭션 하나(DATABASE-DESIGN §6).
- `activity_service.record(...)`는 `db.add()`만 하고 **절대 커밋하지 않는다.** 그래야 업무 변경과 이력이 같은 트랜잭션에 묶인다.
- 서비스 함수가 다른 서비스 함수를 부를 때는 커밋하지 않는 내부 함수(`_remove_member_rows` 등)를 부른다. 회원 탈퇴(P2)가 멤버 제거를 프로젝트마다 반복하는 경우가 여기에 해당한다.

### 4.4 인증과 권한

```python
# core/auth.py
bearer = HTTPBearer(auto_error=False)   # 기본값(True)은 헤더가 없을 때 403을 낸다 → 직접 401로 처리
def get_current_user(cred = Depends(bearer), db = Depends(get_db)) -> User: ...
#  토큰 없음·오류·만료·사용자 없음·탈퇴 → 401 UNAUTHORIZED / is_active=0 → 403 ACCOUNT_DISABLED

# app/services/permissions.py — 역할 비교는 이 파일에서만 한다 (CLAUDE.md §5)
def require_project_role(db, project_id, user, allowed: set[ProjectRole]) -> ProjectMember:
    # 프로젝트 없음 → 404 PROJECT_NOT_FOUND
    # 멤버 아님   → 403 NOT_PROJECT_MEMBER
    # 역할 불일치 → 403 FORBIDDEN
def require_task_edit(member, task, fields: set[str]) -> None:     # TASK-06 권한표
def require_task_delete(member, task) -> None:
```

- 업무 API(`/tasks/{id}`)는 업무를 먼저 조회(없으면 404 `TASK_NOT_FOUND`)한 뒤 `task.project_id`로 `require_project_role`을 부른다. 검사 순서 401 → 422 → 404 → 403 → 400이 자연스럽게 지켜진다.
- 서비스 코드에서 `member.role == "OWNER"` 같은 직접 비교가 보이면 리뷰에서 반려한다.

### 4.5 오류 처리

| 예외 | 처리기 | 응답 |
| --- | --- | --- |
| `AppError(status, code, message)` 와 하위 클래스 (`NotFound`, `Forbidden`, `BusinessRuleError`, `Conflict`) | `core/exceptions.py` | `{ code, message }` |
| `RequestValidationError` | 같은 파일 | 422 `{ code: "VALIDATION_ERROR", message, errors: [{field, message}] }` (API-SPEC §1.4) |
| 없는 경로 (Starlette 404) | 같은 파일 | 404 `NOT_FOUND` |
| DB `IntegrityError` (UNIQUE 위반) | 서비스에서 잡아 `Conflict`로 바꿈 | 409 |
| 그 외 `Exception` | 같은 파일 | 500 `INTERNAL_ERROR`. 상세 내용은 서버 로그에만 남기고 응답에 넣지 않음 |

- 서비스에서 `HTTPException`을 직접 던지지 않는다. 항상 `AppError` 계열을 쓴다.
- 로그에 토큰·비밀번호·`password_hash`를 남기지 않는다.

### 4.6 시각·날짜

- DB의 `DATETIME`은 시간대 정보가 없는 UTC 값이다. 응답 스키마의 공통 타입(`schemas/common.py`)이 UTC로 표시해 `2026-11-12T01:00:00Z` 형태로 내보낸다. 이 타입을 빼먹으면 `Z`가 빠진 시각이 나가서 화면이 9시간 틀린다.
- 저장할 때는 `datetime.now(timezone.utc)`를 쓴다. `datetime.utcnow()`는 쓰지 않는다(Python 3.12에서 사용 중단 예고).
- "오늘"은 `core/clock.py`의 `get_today()` 의존성으로만 얻는다. 테스트는 `app.dependency_overrides`로 날짜를 고정한다.

### 4.7 요청 하나의 흐름 — 업무 상태 변경

```mermaid
sequenceDiagram
  participant UI as 칸반 화면
  participant AX as Axios (core/api)
  participant R as router tasks.py
  participant S as task_service
  participant P as permissions
  participant DB as MariaDB
  UI->>AX: 상태 드롭다운 → IN_PROGRESS
  AX->>R: PATCH /api/tasks/100 {status} + Bearer
  R->>R: get_current_user (401/403) → TaskUpdate 검증 (422)
  R->>S: update_task(db, user, 100, data)
  S->>DB: tasks 조회 (없으면 404)
  S->>P: require_project_role → require_task_edit (403)
  S->>DB: UPDATE tasks · completed_at 처리
  S->>DB: INSERT task_activities (바뀐 필드마다)
  S->>DB: COMMIT (하나라도 실패하면 전체 ROLLBACK)
  S-->>R: Task
  R-->>AX: 200 Task
  AX-->>UI: 두 컬럼 다시 조회 → 토스트
```

## 5. 프론트엔드

### 5.1 폴더

```
frontend/src/
├─ main.jsx · App.jsx          라우터 정의
├─ core/                       ★ 스타터킷
│  ├─ api/client.js            Axios 인스턴스 (baseURL "/api", 인터셉터)
│  ├─ auth/AuthContext.jsx     user, login(), logout(), 시작 시 /users/me로 복원
│  ├─ auth/ProtectedRoute.jsx  비로그인 → /login
│  ├─ ui/                      Button · Modal · ConfirmDialog · Toast(Context) · Avatar · EmptyState · Skeleton · ErrorPage
│  ├─ ui/icons/                lucide SVG 복사본 (UI-DESIGN §5)
│  └─ utils/date.js            todayKst(), 날짜 표시 함수
└─ features/                   동잇 기능
   ├─ auth/                    LoginPage · SignupPage · api.js
   ├─ projects/                ProjectListPage · ProjectCreateModal · ProjectHeader · SettingsPage · MemberSelect · api.js
   └─ tasks/                   BoardPage · TaskCard · StatusSelect · PriorityBadge · DueLabel · TaskFormModal · TaskDetailModal · permissions.js · api.js
```

- 기능 API 호출은 각 `features/*/api.js`에만 둔다. 화면 컴포넌트에서 `axios`를 직접 부르지 않는다.
- 상태 관리는 **인증과 토스트만 Context**로 둔다. 서버 데이터는 각 화면이 `useEffect`로 불러오고, 변경 후에는 다시 불러온다. 같은 불러오기 패턴이 세 번 반복되면 `core/`에 훅으로 뺀다(CLAUDE.md §5).

### 5.2 라우팅

```jsx
<Route path="/login" element={<LoginPage/>} />
<Route path="/signup" element={<SignupPage/>} />
<Route element={<ProtectedRoute><AppLayout/></ProtectedRoute>}>   {/* TopBar 포함 */}
  <Route path="/" element={<Navigate to="/projects" replace/>} />  {/* P1에서 내 대시보드로 */}
  <Route path="/projects" element={<ProjectListPage/>} />
  <Route path="/projects/:id" element={<BoardPage/>}>
    <Route path="tasks/:taskId" element={<TaskDetailModal/>} />   {/* 보드 위에 모달, 주소 유지 */}
  </Route>
  <Route path="/projects/:id/settings" element={<SettingsPage/>} />
  <Route path="*" element={<ErrorPage type="404"/>} />
</Route>
```

### 5.3 API 클라이언트·인증

- 토큰은 localStorage 키 `doingit_token` 하나에만 저장한다. `console.log`로 출력하지 않는다.
- 요청 인터셉터: 토큰이 있으면 `Authorization: Bearer` 헤더를 붙인다.
- 응답 인터셉터: 401이면 토큰 삭제 → 토스트 → `/login`. **단, `/auth/login` 요청은 제외**한다(로그인 실패 문구가 보여야 함). 403 `NOT_PROJECT_MEMBER`·404는 화면이 안내 페이지로 바꾸고, 403 `FORBIDDEN`·400은 토스트로 보여 준다.
- `AuthContext`는 앱 시작 시 토큰이 있으면 `/users/me`를 부르고, 끝날 때까지 `loading` 상태를 둔다. 그래야 새로고침 순간에 로그인 화면이 깜빡이지 않는다.

### 5.4 보안·표시 규칙

- `dangerouslySetInnerHTML` 금지. 업무 설명은 `whitespace-pre-wrap`으로 줄바꿈만 살린다.
- 버튼 숨김은 `features/tasks/permissions.js`의 함수로 판단한다(`project.my_role`, `task.created_by`, `task.assignee`). 이것은 편의 기능이고, 실제 차단은 백엔드가 한다.
- **날짜 함정:** `new Date("2026-11-14")`는 UTC 자정으로 해석돼서 한국 시간으로는 오전 9시가 된다. 마감일(`YYYY-MM-DD`)은 문자열 그대로 `todayKst()` 문자열과 비교한다. 시각(`...Z`)만 `Date`로 바꾼다.

## 6. 설정 (.env)

`.env`는 Git에 올리지 않는다. `.env.example`에는 아래 키를 값 없이(또는 개발용 예시로) 둔다.

| 키 | 예시 | 쓰는 곳 |
| --- | --- | --- |
| `MARIADB_ROOT_PASSWORD` | `change-me` | docker compose |
| `MARIADB_USER`, `MARIADB_PASSWORD` | `doingit`, `change-me` | docker compose, 백엔드 |
| `DATABASE_URL` | `mysql+pymysql://doingit:change-me@localhost:3306/doing_it?charset=utf8mb4` | 백엔드 |
| `TEST_DATABASE_URL` | `...3306/doing_it_test?charset=utf8mb4` | pytest |
| `JWT_SECRET_KEY` | 32자 이상 무작위 문자열 | 백엔드 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | 백엔드 |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | 백엔드 CORS |

- 백엔드는 시작할 때 `JWT_SECRET_KEY`가 없거나 32자보다 짧으면 실행을 멈춘다.

## 7. 테스트

- 테스트 DB는 `doing_it_test` 스키마. 테스트 세션 시작 시 `alembic upgrade head`로 만들고, **테스트 함수마다 모든 테이블을 TRUNCATE**한다. 트랜잭션 롤백 방식은 동시성 테스트(OWNER 동시 제거)가 실제 커밋을 해야 해서 쓰지 않는다.
- `tests/factories.py`에 `make_user`, `make_project(owner)`, `add_member`, `make_task`를 두고 모든 테스트가 같이 쓴다.
- API 호출은 `TestClient`로 하고, 각 테스트는 API-SPEC §10의 필수 경우를 하나씩 담당한다. 권한 테스트에는 403 실패 케이스를 반드시 넣는다.
- 린트: **CI는 두지 않는다.** PR을 올린 사람이 로컬에서 `ruff check`, `black --check`, `npm run lint`, `prettier --check`, `pytest`를 돌리고, PR 설명에 결과를 한 줄 적는다. 리뷰어는 그 줄이 없으면 승인하지 않는다(성공 기준 5).
- 비밀번호 검증(AUTH-01): 8~64자 **그리고** UTF-8 72바이트 이하. 72바이트를 넘으면 422 — bcrypt가 72바이트를 넘는 값을 받지 않기 때문이다. 경계값(64자, 73바이트 한글) 테스트를 넣는다.

## 8. 스프린트 1 첫날 작업 순서

```mermaid
flowchart LR
  B1["BE-B 서승범<br/>compose · init.sql<br/>Alembic 0001 · seed"] --> B2["BE-A 양준석<br/>인증 API<br/>프로젝트·멤버 API"]
  A1["BE-A 양준석<br/>core: config·db·security<br/>auth·exceptions·clock"] --> B2
  F1["FE-A 최진영<br/>Vite·Tailwind 세팅<br/>core: api·auth·ui"] --> F2["FE-A<br/>로그인·목록·설정"]
  F3["FE-B 김서현<br/>보드·카드 퍼블리싱<br/>(목 데이터)"] --> F4["FE-B<br/>API 연결 (스프린트 2)"]
  F1 --> F3
  B2 --> F2
```

| 순서 | 담당 | 결과물 | 막히는 사람 |
| :-: | --- | --- | --- |
| 1 | BE-B | `docker compose up` → `alembic upgrade head` → `seed.py`까지 동작 | 백엔드 전원 |
| 1 | BE-A | `backend/core/` 전체 + `/api/health` | 백엔드 전원 |
| 1 | FE-A | Vite 프로젝트 + 프록시 + `core/` 뼈대 + Tailwind 토큰 | 프론트 전원 |
| 2 | BE-A | AUTH-01~04 + pytest | FE-A 로그인 연결 |
| 2 | FE-B | 칸반·카드·모달 화면을 목 데이터로 먼저 | — |

## 9. 배포 (P2)

- 11/26 발표는 발표자 PC에서 로컬로 시연한다. 전날 `seed.py`로 시연 데이터를 넣고, 시연 순서대로 한 번 리허설한다.
- 클라우드 배포는 P2 수준의 선택 작업이다. P0·P1이 끝나고 마무리 단계에 시간이 남을 때만 시도하고, 맞지 않으면 버린다. **REQUIREMENTS에는 등록하지 않고 이 문서에서만 관리한다.** 시도할 때는 이 절에 대상 서비스·DB 위치·비용을 먼저 적는다.

## 10. 결정 기록 (2026-11-12)

| # | 항목 | 결정 | 반영할 문서 |
| :-: | --- | --- | --- |
| 1 | Python · Node · MariaDB | 3.12 · 22 LTS · 10.11 | 이 문서 §2, CONSTITUTION §5 |
| 2 | React · Tailwind | 19 · 4 (색 토큰은 CSS `@theme`) | 이 문서 §2, UI-DESIGN §7 |
| 3 | docker compose 범위 | MariaDB만 | 이 문서 §1 |
| 4 | 시연·배포 | 로컬 시연. 배포는 여유 있을 때만, 요구사항에는 등록하지 않음 | 이 문서 §9 |
| 5 | 비밀번호 길이 | 8~64자 + UTF-8 72바이트 이하 | REQUIREMENTS AUTH-01, API-SPEC §5.1, SPEC |
| 6 | 프론트 폴더 | `core/` + `features/`만 | CLAUDE.md §4 |
| 7 | CI | 두지 않음. 로컬 린트·pytest 결과를 PR 설명에 적음 | 이 문서 §7, CONSTITUTION(PR 규칙) |
