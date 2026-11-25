# 동잇 (Doing_It)

팀이 프로젝트 단위로 업무를 등록하고 담당자·마감일·우선순위를 정해 칸반 보드로 관리하는 웹 서비스입니다.
업무 **변경 이력**과 **마감 임박·지연 대시보드**로 "누가 언제 무엇을 바꿨는지", "무엇이 늦어지는지"를 한눈에 봅니다.

> **현재 단계:** 스프린트 0 (명세·설계) 완료, 11/13 개발 환경 세팅, 11/16 스펙 v1.0 동결 — 11/16 스프린트 1부터 코드 작성. 처음이라면 [docs/PROJECT-OVERVIEW.md](docs/PROJECT-OVERVIEW.md)부터 읽어 주세요.

## 주요 기능

- **MVP (11/19까지):** 회원가입·로그인, 프로젝트·멤버 관리, 업무 CRUD, 버튼식 칸반, 변경 이력 자동 기록
- **이후 (P1):** 진행률, 검색·필터, 댓글, 이력 조회, 마감 임박·지연, 내 대시보드
- 전체 목록과 우선순위: [docs/REQUIREMENTS.md §7](docs/REQUIREMENTS.md)

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Frontend | React 19, JavaScript, Vite, React Router, Tailwind CSS 4, Axios, React Hooks + Context API (Node 22 LTS) |
| Backend | Python 3.12, FastAPI, Pydantic 2, Uvicorn, python-dotenv |
| DB / ORM | MariaDB 10.11 LTS (Docker), SQLAlchemy 2.x, Alembic, PyMySQL |
| Auth | JWT Access Token (2시간, localStorage, PyJWT), bcrypt |
| Test | pytest + httpx (P0 핵심 API), Postman |
| Lint / Format | ruff + black / ESLint + Prettier |

목록에 없는 라이브러리는 팀 합의 없이 추가하지 않습니다 ([CONSTITUTION §5](docs/CONSTITUTION.md)).

### 의존성 추가 기록 (CONSTITUTION 5-1)

과정 기준표 외에 팀 합의로 추가한 라이브러리와 이유입니다.

| 라이브러리 | 영역 | 이유 |
| --- | --- | --- |
| ruff, black / ESLint, Prettier | 코드 스타일 | 4명과 AI가 쓴 코드를 한 형식으로 맞춰 리뷰 시간을 줄인다 |
| Uvicorn | 백엔드 | FastAPI 앱을 실행하는 ASGI 서버 |
| python-dotenv | 백엔드 | `.env`의 비밀 값을 코드에 넣지 않고 읽는다 |
| PyJWT | 인증 | JWT Access Token 발급·검증 (HS256) |
| bcrypt | 인증 | 비밀번호 해시 저장 |
| httpx | 테스트 | pytest에서 FastAPI `TestClient`로 API를 호출할 때 필요 |
| Vite | 프론트엔드 | React 개발 서버·빌드 도구 |
| React Router | 프론트엔드 | `/projects/:id/tasks/:taskId` 같은 화면 주소 유지(새로고침·공유) |

## 시작하기

> 🚧 코드 작성 후 채웁니다. 아래는 확정된 부분만 적었습니다.
> 처음 세팅하는 팀원은 단계별 안내 [docs/SETUP.md](docs/SETUP.md)를 따라 하면 됩니다(Windows PowerShell 기준, 막힐 때 해결법 포함).

### 0. 준비물

| 프로그램 | 버전 | 누가 |
| --- | --- | --- |
| Git | 아무 버전 | 전원 |
| Docker Desktop | 최신 | 전원 (DB를 띄우는 데 필요) |
| Python | **3.12** | 백엔드. 프론트도 깔아 두면 백엔드를 직접 띄워 볼 수 있다 |
| Node | 22 LTS | 프론트엔드 |

확인: `docker --version`, `py -3.12 --version`

### 1. 환경 변수

```bash
cp .env.example .env   # .env는 Git에 올리지 않습니다 (cmd 창이면: copy .env.example .env)
# MARIADB_PASSWORD의 change-me를 바꾸면 DATABASE_URL·TEST_DATABASE_URL 안의 비밀번호도 같이 바꾼다
# JWT_SECRET_KEY 만들기:
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

| 변수 | 설명 | 예시 |
| --- | --- | --- |
| `MARIADB_ROOT_PASSWORD` | DB 관리자 비밀번호 (docker compose) | 각자 설정 |
| `MARIADB_USER` / `MARIADB_PASSWORD` | DB 계정 (docker compose·백엔드) | `doingit` / 각자 설정 |
| `DATABASE_URL` | 개발 DB 접속 주소 | `mysql+pymysql://doingit:비밀번호@localhost:3307/doing_it?charset=utf8mb4` |
| `TEST_DATABASE_URL` | pytest 전용 DB | `...@localhost:3307/doing_it_test?charset=utf8mb4` |
| `JWT_SECRET_KEY` | 토큰 서명 키 (HS256) | 32자 이상 임의 문자열 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 토큰 만료(분) | `120` |
| `FRONTEND_ORIGIN` | CORS 허용 주소 | `http://localhost:5173` |

변수 목록의 기준은 [docs/ARCHITECTURE.md §6](docs/ARCHITECTURE.md)입니다.

### 2. DB (MariaDB 10.11, Docker)

Docker Desktop을 먼저 켜 둔다. PC 쪽 포트는 **3307**이다(수업 PC의 MariaDB가 3306을 쓰므로. 컨테이너 안은 3306).

```bash
docker compose up -d --wait   # MariaDB만 컨테이너로 실행 (doing_it, doing_it_test 스키마 생성)
docker compose ps             # STATUS에 healthy가 보이면 성공 (처음 한 번은 1~3분)
```

끄기: `docker compose stop` (데이터 유지) · 다시 켜기: `docker compose start`

### 3. 백엔드

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt   # 실행 + 테스트·린트 패키지 전부
```

DB 접속 확인 — 아래 두 줄이 나오면 성공:

```bash
python -c "from dotenv import dotenv_values; from sqlalchemy import create_engine, text; v=dotenv_values('.env'); [print(k, create_engine(v[k]).connect().execute(text('SELECT DATABASE()')).scalar()) for k in ('DATABASE_URL','TEST_DATABASE_URL')]"
# DATABASE_URL doing_it
# TEST_DATABASE_URL doing_it_test
```

_마이그레이션·서버 실행 명령 작성 예정_

### 4. 프론트엔드

Node **22 LTS**가 필요하다(`package.json`의 `engines`). 확인: `node --version` → `v22.x`

```bash
cd frontend
npm install          # 처음 한 번, package.json이 바뀌었을 때 다시
npm run dev          # 개발 서버 → http://localhost:5173
```

- 화면이 API를 부르려면 **백엔드(3번)가 8000 포트에 켜져 있어야** 한다. 프론트는 `/api`로 시작하는 요청을 Vite 프록시로 `http://localhost:8000`에 넘긴다(`vite.config.js`). 그래서 프론트용 `.env`는 따로 없다.
- 백엔드 CORS는 `.env`의 `FRONTEND_ORIGIN=http://localhost:5173`만 허용하므로 **5173 포트로 열어야** 한다.

| 명령 (`frontend/` 안에서) | 하는 일 |
| --- | --- |
| `npm run dev` | 개발 서버 (코드를 고치면 화면이 바로 바뀜) |
| `npm run lint` | ESLint 검사 — PR 전에 통과 |
| `npm run format:check` | Prettier 형식 검사 — PR 전에 통과 (`npm run format`은 자동으로 고침) |
| `npm run build` | 배포용 파일을 `frontend/dist/`에 만든다 |
| `npm run preview` | 만든 `dist/`를 미리 보기 |

### 자주 나는 문제

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| `.env에 MARIADB_…를 넣어 주세요` | `.env` 파일이 없음 | 1번 `cp .env.example .env` |
| `port is already allocated` / 3307 사용 중 | 다른 프로그램이 3307을 씀 | 팀(DB 담당 서승범)에 알리기 |
| `Access denied for user 'doingit'` | `.env` 비밀번호를 바꿨는데 DB는 예전 비밀번호로 이미 만들어짐 | `docker compose down -v` 후 2번 다시 (**DB 데이터가 지워짐**) |
| `docker: command not found` / 연결 오류 | Docker Desktop이 꺼져 있음 | Docker Desktop 실행 후 1분 기다리기 |
| `pip install` 실패 | Python 버전이 3.12가 아님 | `.venv` 폴더를 지우고 `py -3.12 -m venv .venv`로 다시 만들기 |
| PowerShell activate 시 "스크립트를 실행할 수 없으므로…" | Windows 기본 보안 설정 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 한 번 실행 후 다시 activate |

## 폴더 구조 (확정 — 상세는 [docs/ARCHITECTURE.md §3](docs/ARCHITECTURE.md))

```
docs/                    명세 문서
docker-compose.yml       MariaDB만
backend/app/             routers · services · models · schemas
backend/core/            ★ 공통: 설정, DB 세션, 보안, 인증 의존성, 예외 처리
backend/alembic/ · backend/scripts/seed.py · backend/tests/
frontend/src/features/   auth · projects · tasks
frontend/src/core/       ★ 공통: API 클라이언트, 인증 Context, 공통 UI, 아이콘
postman/                 Postman 컬렉션
```

★ = 다른 프로젝트에서 재사용할 스타터킷

## 문서

| 문서 | 내용 |
| --- | --- |
| [PROJECT-OVERVIEW](docs/PROJECT-OVERVIEW.md) | 1페이지 소개 |
| [PROPOSAL](docs/PROPOSAL.md) | 기획서 (최상위 근거) |
| [CONSTITUTION](docs/CONSTITUTION.md) | 팀 규칙 |
| [REQUIREMENTS](docs/REQUIREMENTS.md) | 기능 ID·우선순위·권한 |
| [SPEC](docs/SPEC.md) | 기능 스펙 (Given-When-Then) |
| [USER-STORIES](docs/USER-STORIES.md) | 사용자 스토리 |
| [DATABASE-DESIGN](docs/DATABASE-DESIGN.md) | DB 설계 |
| [API-SPEC](docs/API-SPEC.md) | API 명세 |
| [UI-DESIGN](docs/UI-DESIGN.md) | 화면 설계 |
| [COMPONENTS](docs/COMPONENTS.md) | 프론트 공통 컴포넌트 목록·사용법 (UI-DESIGN과 다르면 UI-DESIGN을 따름) |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 폴더·계층·버전·실행 환경 |
| [PRD](docs/PRD.md) | 기능·스토리 연결표 |
| [TASKS](docs/TASKS.md) | 태스크 분해·담당·일정 |
| [SPEC-CHANGELOG](docs/SPEC-CHANGELOG.md) | 스펙 v1.0 동결 후 변경 이력 |

문서끼리 다르면 위쪽(기획서 → 헌법 → 요구사항) 문서를 따릅니다.

### 과정 가이드 산출물 이름과의 대응

이름은 바꾸지 않고 아래처럼 대응합니다(11/16 회의 결정).

| 가이드 산출물 | 이 저장소 문서 |
| --- | --- |
| spec.md | [docs/SPEC.md](docs/SPEC.md) (기능 ID·우선순위는 [REQUIREMENTS](docs/REQUIREMENTS.md)) |
| plan.md | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| data-model.md | [docs/DATABASE-DESIGN.md](docs/DATABASE-DESIGN.md) |
| api-contract.md | [docs/API-SPEC.md](docs/API-SPEC.md) |
| tasks.md | [docs/TASKS.md](docs/TASKS.md) |

## 협업 규칙

- **브랜치:** `feat/TASK-02-status-change`, `fix/AUTH-01-login-id-dup` — `main`에 직접 push 금지
- **커밋:** `종류(기능 ID): 한국어 설명` — 예: `feat(TASK-02): 업무 상태 변경 API 추가`
- **PR:** 리뷰 1명 승인 + ruff·black·ESLint·Prettier 통과 후 병합. CI가 없으므로 로컬 실행 결과(백엔드는 pytest 포함)를 PR 설명에 한 줄 적는다
- **리뷰어:** 조 안에서 영역을 바꿔 고정(양준석 ↔ 최진영, 서승범 ↔ 김서현). `core/`·마이그레이션 PR은 같은 영역 리뷰어(양준석 ↔ 서승범, 최진영 ↔ 김서현)를 한 명 더 넣는다(CONSTITUTION 3-2)
- **완료 기준:** P0 핵심 API는 pytest 통과(권한 실패 403 케이스 포함)

## 팀

| 이름 | 역할 |
| --- | --- |
| 양준석 | Backend · 팀장 (A조) |
| 최진영 | Frontend (A조) |
| 서승범 | Backend (DB·테스트) · 예비 팀장 (B조) |
| 김서현 | Frontend (B조) |

일정: 2026-11-10 ~ 11-26 · **11/19 P0 완료 게이트** · 11/26 최종 발표
