# Project: 동잇 (Doing_It) — 팀 협업 프로젝트 관리 시스템

> 이 파일은 Claude가 이 저장소에서 작업할 때 따르는 지침이다.
> 근거 문서: docs/PROPOSAL.md(기획서) → docs/CONSTITUTION.md(헌법) → docs/REQUIREMENTS.md · docs/SPEC.md(기능 스펙 F1~F5, Given-When-Then — 기능 ID·우선순위는 REQUIREMENTS 우선) · docs/USER-STORIES.md · docs/DATABASE-DESIGN.md · docs/API-SPEC.md · docs/UI-DESIGN.md · docs/ARCHITECTURE.md(폴더·계층·버전) → 코드.
> 빠른 요약: docs/PROJECT-OVERVIEW.md(처음 보는 사람용 1페이지 소개 — 기획서와 다르면 기획서를 따른다), docs/PRD.md(목표·사용자·MoSCoW 기능·스토리 연결 안내 — 원본 문서가 우선, 새 ID를 만들지 않는다).
> 문서끼리 충돌하면 앞쪽 문서를 따른다. 이 파일과 docs가 다르면 docs가 우선이며, 이 파일을 docs에 맞게 고친다.

## 1. Overview
- **목적:** 팀이 프로젝트 단위로 업무를 등록하고 담당자·마감일·우선순위를 지정해 칸반 보드로 진행 상황을 관리하는 웹 서비스.
- **차별화 기능:** 업무 변경 이력(Activity Log), 마감 임박(3일 이내)·지연 업무 대시보드.
- **팀·일정:** 4명(BE 2, FE 2), 2026-11-10 ~ 11-26, 총 92시간. **11/19 P0 완료 게이트**, 11/26 최종 발표.
- **개발 방식:** SDD — 명세 작성 → AI 구현 → 코드 검토 → 테스트 → 명세와 비교.
- **현재 단계:** 스프린트 0(명세·설계) 완료 — 11/12 설계 확정. 11/13 스프린트 1(MVP 1) 시작. 코드는 아직 없음.
- **시연:** 로컬(발표자 PC + Docker MariaDB + 시드 데이터). 클라우드 배포는 여유 있을 때만(ARCHITECTURE §9).

## 2. Tech Stack (고정 — 목록에 없는 라이브러리 추가 금지)
| 영역 | 기술 |
| --- | --- |
| Frontend | React 19, JavaScript, Vite(빌드), React Router(화면 주소), Tailwind CSS 4, Axios, React Hooks + Context API — Node 22 LTS |
| Backend | Python 3.12, FastAPI, Pydantic 2, Uvicorn(ASGI 서버), python-dotenv(.env 읽기) |
| DB / ORM | MariaDB 10.11 LTS(Docker), SQLAlchemy 2.x, Alembic, PyMySQL |
| Auth | JWT Access Token(만료 2시간, localStorage, PyJWT), bcrypt |
| Test | pytest + httpx(TestClient)(P0 핵심 API), Postman(그 외, 컬렉션 저장소에 포함) |
| Lint / Format | BE: ruff + black / FE: ESLint + Prettier |

- 쓰지 않는 패키지: passlib(bcrypt 직접 사용), python-multipart(로그인은 JSON), tzdata(UTC+9 고정), 아이콘·차트·상태관리 라이브러리. 상세는 ARCHITECTURE §2.

## 3. 범위 규칙
- 기능은 REQUIREMENTS.md의 **기능 ID(예: TASK-01)와 수용 기준이 있어야** 구현한다.
- **P0이 모두 끝나고 테스트가 통과하기 전에는 P1·P2 작업을 하지 않는다.**
- 만들지 않는 것: LLM, RAG, LangChain, AI 에이전트, AI 모델 학습 등 AI 기능, WebSocket 실시간 알림, 이메일 발송, 파일 첨부, 외부 서비스 연동, VIEWER 역할.
- 명세에 없는 API·테이블·라이브러리를 만들지 않는다. 필요하면 바로 구현하지 말고 명세 수정을 제안한다(새 아이디어는 P2로 등록).
- 칸반 상태 변경은 버튼(드롭다운) 방식. 드래그 앤 드롭은 P2.

## 4. Directory Structure (확정 — 상세는 docs/ARCHITECTURE.md §3~§5)
```
docs/            명세 문서 (PROPOSAL, CONSTITUTION, REQUIREMENTS, SPEC, USER-STORIES, DATABASE-DESIGN, API-SPEC, UI-DESIGN, ARCHITECTURE, PRD, PROJECT-OVERVIEW)
docker-compose.yml  MariaDB만
backend/app/     routers/ · services/ · models/ · schemas/ · main.py
backend/core/    ★ 스타터킷: config, DB 세션, 보안(bcrypt·JWT), 인증 의존성, 공통 예외 처리, clock(한국 날짜), 페이지네이션
backend/alembic/ · backend/scripts/seed.py · backend/tests/
frontend/src/features/  auth/ · projects/ · tasks/ (화면·기능별 컴포넌트와 api.js)
frontend/src/core/ ★ 스타터킷: API 클라이언트(Axios), 인증 Context, 공통 UI, 아이콘(SVG), 날짜 유틸
```
- 계층: 라우터(요청 검증·인증 의존성) → 서비스(권한 검사·업무 로직·이력 기록·커밋) → 모델.
- ★ `core/`는 `app/`·`features/`를 import하지 않는다(스타터킷 재사용).
- 엔드포인트는 `async def`가 아니라 `def`로 쓴다(동기 DB 드라이버). 이력 기록 함수는 커밋하지 않는다.

## 5. Coding Principles
### 백엔드
- 권한 검사는 **백엔드 서비스 계층의 공통 함수 `require_project_role(...)`** 로만 한다. 역할 값을 직접 비교하지 않는다.
- 프로젝트 하위 리소스(업무·댓글·이력) 접근 시 항상 프로젝트 멤버인지 먼저 확인한다.
- 인증 없이 호출할 수 있는 API는 회원가입·로그인뿐이다.
- 업무 생성, 상태·담당자·마감일·우선순위 변경, 삭제는 **같은 트랜잭션에서 `task_activities`에 기록**한다. 바뀐 항목마다 1행씩 남긴다.
- 삭제는 실제 삭제(CASCADE). 업무가 삭제돼도 이력은 `task_id = NULL`로 남긴다.
- DB로 막을 수 있는 규칙은 UNIQUE·CHECK·FK로, 여러 행에 걸친 규칙(OWNER 최소 1명)은 서비스 계층에서 검사한다.
- 상태·역할은 Python `enum.Enum`으로 정의하고, DB에는 VARCHAR + CHECK로 저장한다(MariaDB ENUM 타입 금지).
- 스키마 변경은 **Alembic 마이그레이션으로만** 한다. DDL을 직접 실행하지 않는다.
- 시각은 UTC로 저장하고 ISO 8601(`Z`)로 응답한다. 문자셋은 utf8mb4. PostgreSQL 전용 문법(`FILTER` 등)은 쓰지 않는다.
- 응답에 `password_hash`를 포함하지 않는다. 비밀 값은 `.env`로 관리하고 저장소에는 `.env.example`만 둔다.

### API
- REST: 복수형 명사 + HTTP 메서드 (`GET /projects/{id}/tasks`, `PATCH /tasks/{id}`).
- 모든 API 경로 앞에 **`/api`** 를 붙인다(예: `/api/projects`). 개발 중 프론트는 Vite 프록시로 호출하고, 백엔드 CORS는 `.env`의 `FRONTEND_ORIGIN`만 허용한다.
- 성공: 리소스 객체 또는 `{ "items": [...], "total": n, "page": 1, "size": 20 }`. 목록은 페이지네이션 기본 20건, 최대 100건. 집계 API는 페이지네이션하지 않는다.
- 실패: `{ "code": "ASSIGNEE_NOT_MEMBER", "message": "한국어 메시지" }`. 422는 여기에 `errors: [{ "field", "message" }]`를 더한다(FastAPI 기본 `detail` 형식은 공통 예외 처리에서 변환).
- 상태 코드: 400 업무 규칙 위반 · 401 인증 실패 · 403 권한 없음 · 404 없음 · 409 중복 · 422 입력 검증 실패. 검사 순서는 401 → 422 → 404 → 403 → 400.
- 마감 임박·지연의 "오늘"은 한국 날짜(UTC+9 고정)로 서버에서 계산한다.
- API를 바꿀 때는 **API-SPEC.md를 먼저 수정**한다.

### 프론트엔드
- `dangerouslySetInnerHTML` 금지. 토큰을 콘솔이나 로그에 출력하지 않는다.
- Axios 인터셉터에서 JWT 헤더를 붙이고, 401을 받으면 토큰을 삭제하고 로그인 화면으로 이동한다.
- 버튼 숨김은 편의 기능일 뿐, 권한 처리로 보지 않는다.
- 비로그인 사용자는 로그인 화면으로 보내고, 403·404는 안내 화면을 보여준다.

### 이름·언어
- 문서·커밋·PR 설명·코드 주석은 **한국어**, 식별자·파일·API 경로·DB 이름은 **영어**.
- Python: `snake_case` / 클래스 `PascalCase`. JavaScript: `camelCase` / 컴포넌트 `PascalCase`. DB 테이블: 복수형 `snake_case`.
- 같은 코드가 세 번 반복될 때 공통화한다. 지금 필요 없는 추상화는 만들지 않는다.

## 6. Workflow
- 커밋: `종류(기능 ID): 한국어 설명` — 종류는 feat|fix|refactor|test|docs|chore. 예: `feat(TASK-02): 업무 상태 변경 API 추가`
- 브랜치: `feat/TASK-02-status-change`, `fix/AUTH-01-login-id-dup`. `main`에 직접 push 금지, PR 리뷰 1명 승인 후 병합.
- PR 전에 ruff·black·ESLint·Prettier(백엔드는 pytest도)를 로컬에서 통과시키고, **PR 설명에 결과를 한 줄 적는다.** CI는 두지 않으므로 리뷰어는 이 줄이 없으면 승인하지 않는다.
- P0 핵심 API(인증·권한·업무 CRUD)는 pytest가 통과해야 완료로 본다. 권한 테스트에는 **실패 케이스(403)를 반드시 포함**한다.

## 7. Response Guidelines (For Claude)
- 작업은 **초안 → 피드백 → 반영** 순서로 한다. 명시적인 실행 지시가 있을 때만 파일을 만들거나 수정한다.
- 코드를 요청받으면 관련 기능 ID와 해당 명세 부분을 확인하고, 응답에 근거 기능 ID를 밝힌다.
- 명세와 다르거나 명세에 없는 것이 필요하면 코드보다 먼저 명세 수정을 제안한다.
- 권한 누락, XSS, 트랜잭션 누락 같은 보안·무결성 약점은 제안할 때 함께 지적한다.
