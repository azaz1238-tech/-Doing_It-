# Project: TeamBoard (팀 협업 프로젝트 관리 시스템)

> 이 파일은 Claude가 이 저장소에서 작업할 때 따르는 지침이다.
> 근거 문서: docs/PROPOSAL.md(기획서) → docs/CONSTITUTION.md(헌법) → docs/REQUIREMENTS.md · docs/USER-STORIES.md · docs/DATABASE.md · docs/API-SPEC.md(작성 예정) → 코드.
> 빠른 요약: docs/IDEA.md(기획서 한 장 요약 — 기획서와 다르면 기획서를 따른다).
> 문서끼리 충돌하면 앞쪽 문서를 따른다. 이 파일과 docs가 다르면 docs가 우선이며, 이 파일을 docs에 맞게 고친다.

## 1. Overview
- **목적:** 팀이 프로젝트 단위로 업무를 등록하고 담당자·마감일·우선순위를 지정해 칸반 보드로 진행 상황을 관리하는 웹 서비스.
- **차별화 기능:** 업무 변경 이력(Activity Log), 마감 임박(3일 이내)·지연 업무 대시보드.
- **팀·일정:** 4명(BE 2, FE 2), 2026-11-10 ~ 11-26, 총 92시간. **11/19 P0 완료 게이트**, 11/26 최종 발표.
- **개발 방식:** SDD — 명세 작성 → AI 구현 → 코드 검토 → 테스트 → 명세와 비교.
- **현재 단계:** 스프린트 0(명세·설계). 코드는 아직 없음.

## 2. Tech Stack (고정 — 목록에 없는 라이브러리 추가 금지)
| 영역 | 기술 |
| --- | --- |
| Frontend | React, JavaScript, Tailwind CSS, Axios, React Hooks + Context API |
| Backend | Python, FastAPI, Pydantic |
| DB / ORM | MariaDB 10.11 LTS(Docker), SQLAlchemy 2.x, Alembic, PyMySQL |
| Auth | JWT Access Token(만료 2시간, localStorage), bcrypt |
| Test | pytest(P0 핵심 API), Postman(그 외, 컬렉션 저장소에 포함) |
| Lint / Format | BE: ruff + black / FE: ESLint + Prettier |

## 3. 범위 규칙
- 기능은 REQUIREMENTS.md의 **기능 ID(예: TASK-01)와 수용 기준이 있어야** 구현한다.
- **P0이 모두 끝나고 테스트가 통과하기 전에는 P1·P2 작업을 하지 않는다.**
- 만들지 않는 것: LLM, RAG, LangChain, AI 에이전트, AI 모델 학습 등 AI 기능, WebSocket 실시간 알림, 이메일 발송, 파일 첨부, 외부 서비스 연동, VIEWER 역할.
- 명세에 없는 API·테이블·라이브러리를 만들지 않는다. 필요하면 바로 구현하지 말고 명세 수정을 제안한다(새 아이디어는 P2로 등록).
- 칸반 상태 변경은 버튼(드롭다운) 방식. 드래그 앤 드롭은 P2.

## 4. Directory Structure (제안 — 팀 확정 필요)
```
docs/            명세 문서 (IDEA, PROPOSAL, CONSTITUTION, REQUIREMENTS, USER-STORIES, DATABASE, API-SPEC)
backend/app/     routers/ · services/ · models/ · schemas/
backend/core/    ★ 스타터킷: 인증, DB 세션, 공통 예외 처리
backend/tests/   pytest
frontend/src/    pages/ · components/ · features/
frontend/src/core/ ★ 스타터킷: API 클라이언트(Axios), 인증 Context, 공통 UI
```
- 계층: 라우터(요청 검증·인증 의존성) → 서비스(권한 검사·업무 로직·이력 기록) → 모델.
- ★ 공통 모듈은 처음부터 분리된 폴더에 둔다(스타터킷 재사용).

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
- 성공: 리소스 객체 또는 `{ "items": [...], "total": n, "page": 1, "size": 20 }`. 목록은 페이지네이션 기본 20건.
- 실패: `{ "code": "ASSIGNEE_NOT_MEMBER", "message": "한국어 메시지" }`.
- 상태 코드: 400 업무 규칙 위반 · 401 인증 실패 · 403 권한 없음 · 404 없음 · 409 중복 · 422 입력 검증 실패(Pydantic, 필드별 오류).
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
- 브랜치: `feat/TASK-02-status-change`, `fix/AUTH-01-email-dup`. `main`에 직접 push 금지, PR 리뷰 1명 승인 후 병합.
- PR 전에 ruff·black·ESLint·Prettier를 통과시킨다.
- P0 핵심 API(인증·권한·업무 CRUD)는 pytest가 통과해야 완료로 본다. 권한 테스트에는 **실패 케이스(403)를 반드시 포함**한다.

## 7. Response Guidelines (For Claude)
- 작업은 **초안 → 피드백 → 반영** 순서로 한다. 명시적인 실행 지시가 있을 때만 파일을 만들거나 수정한다.
- 코드를 요청받으면 관련 기능 ID와 해당 명세 부분을 확인하고, 응답에 근거 기능 ID를 밝힌다.
- 명세와 다르거나 명세에 없는 것이 필요하면 코드보다 먼저 명세 수정을 제안한다.
- 권한 누락, XSS, 트랜잭션 누락 같은 보안·무결성 약점은 제안할 때 함께 지적한다.
