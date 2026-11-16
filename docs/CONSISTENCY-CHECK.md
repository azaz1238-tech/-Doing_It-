# 일관성 점검 결과 · 회의 안건 (CONSISTENCY-CHECK.md)

> 프로젝트: 동잇(Doing_It) | 버전: v1.0 (**결정·반영 완료** — 2026-11-16 회의, 각 문서 스펙 v1.0 동결) · v0.2 (결정 칸 기록) · v0.1 (회의 전) | 작성일: 2026-11-13 · 수정일: 2026-11-16 | 작성: 서승범(팀장 부재로 대신 작성) | 4일차 산출물 D4-01
> 대상: PROPOSAL · CONSTITUTION · REQUIREMENTS v0.8 · SPEC v0.5 · USER-STORIES v0.7 · DATABASE-DESIGN v0.6 · API-SPEC v0.4 · UI-DESIGN v0.2 · ARCHITECTURE v0.1 · PRD · PROJECT-OVERVIEW · README · CLAUDE.md · tasks.md v0.3 · `.env.example` · `requirements.txt` · 강의 일별 가이드
> 아래 "대상"의 버전은 점검 당시 값이다. 반영 내용은 [SPEC-CHANGELOG.md](./SPEC-CHANGELOG.md) #1에 있다.
> 이 문서는 [tasks.md](./tasks.md) §9 "팀 확인 필요" 항목과 이번 점검 결과를 합친 것이다. **회의에서 결정 칸을 채운 뒤, 그 결정대로 각 문서를 고친다.** 그 전에는 다른 문서를 고치지 않는다.

## 1. 회의 안건

결정 칸은 회의에서 채운다. "고칠 곳"은 결정 후 수정할 문서다.

### 1.1 역할 · 운영

| # | 안건 | 지금 상태 (근거) | 제안 | 결정 | 고칠 곳 |
| :-: | --- | --- | --- | --- | --- |
| 1 | tasks.md 조 편성 채택 | tasks.md v0.3은 "제안". CONSTITUTION §3-1 역할표는 대시보드 API를 BE-B, 대시보드·통계 화면을 FE-B로 둠. tasks.md는 DASH-01·03·04를 양준석, 해당 화면을 최진영에게 둠 | 조 편성(A조 양준석·최진영 / B조 서승범·김서현) 채택 | 제안대로 채택 → tasks.md v1.0 | tasks.md v1.0, CONSTITUTION §3-1 |
| 2 | 리뷰 방식 | CONSTITUTION §3-2 "다른 영역 담당자도 돌아가며, 같은 사람끼리만 리뷰하지 않게" ↔ tasks.md §8-4 "조 안에서 영역 교차 고정 리뷰" | 조 안 고정 리뷰 + `core/`·마이그레이션은 같은 영역 리뷰어 추가. 헌법 문구를 이에 맞춤 | 제안대로 (조 안 고정 리뷰 + 같은 영역 리뷰어 추가) | CONSTITUTION §3-2 또는 tasks.md §8 |
| 3 | 팀장 부재 시 예비 대행 | tasks.md §2: 예비 서승범이 회의·병합·스펙 변경 이력 승인·진행 현황 대행. 명세 수정 결정은 미룸 | 그대로 채택. 서승범에게 GitHub 관리 권한(병합·브랜치 보호) 부여 | 제안대로 (서승범 대행 + GitHub 관리 권한) | CONSTITUTION §3, GitHub 설정 |

### 1.2 일정

| # | 안건 | 지금 상태 (근거) | 제안 | 결정 | 고칠 곳 |
| :-: | --- | --- | --- | --- | --- |
| 4 | 코딩 시작일 | 가이드: 11/16(5일차) 코딩 시작. 문서: 11/13 스프린트 1 시작 (PROPOSAL §7, README, CLAUDE.md) | 가이드 기준. 11/13은 설계 마감·개발 환경 세팅 | 제안대로 (코딩 11/16 시작, 11/13은 설계 마감·환경 세팅) | PROPOSAL §7, README, CLAUDE.md |
| 5 | F2(업무·칸반) 완료일 | 가이드: 11/17 완료. 문서: 스프린트 2(11/17 오후~11/19) | 11/17로 앞당기고 11/18 오전을 버퍼로 | 제안대로 (11/17 완료, 11/18 오전 버퍼) | PROPOSAL §7, tasks.md |
| 6 | 7일차 F4 범위 | 가이드: F4 API·화면 구현. F4에 P1(댓글·이력 조회)이 섞여 있고, P0 전 P1 금지 (CONSTITUTION §4-1) | 7일차엔 LOG-01·02(P0)만. 댓글·이력 조회는 게이트 후 | 제안대로 (7일차는 LOG-01·02만) | tasks.md |
| 7 | P1 기간 | 가이드: 11/24 기능 동결(M3). 문서: P1 11/23~24 | P1은 11/19 오후~11/23, 1순위 6개만 목표 | 제안대로 (11/19 오후~11/23, 1순위 6개) | tasks.md, REQUIREMENTS 일정 |

### 1.3 명세 · 도구

| # | 안건 | 지금 상태 (근거) | 제안 | 결정 | 고칠 곳 |
| :-: | --- | --- | --- | --- | --- |
| 8 | "JWT·OAuth2" 의미 | 가이드 6일차 "JWT·OAuth2". 우리는 JSON 로그인, `python-multipart` 미사용 (API-SPEC §5.1, ARCHITECTURE §2) | **강사에게 확인.** Bearer 토큰 헤더는 이미 OAuth2 Bearer 규격이므로 폼 로그인은 쓰지 않는 쪽 | **OAuth2 Bearer 규격 사용.** `Authorization: Bearer` 헤더(RFC 6750)를 FastAPI `HTTPBearer`로 읽는다. 로그인은 JSON 유지, 폼 로그인·`python-multipart` 미사용 | (필요 시) API-SPEC §5.1 |
| 9 | Postman 범위 | 가이드: F1~F4 Postman 컬렉션. CLAUDE.md·CONSTITUTION 0-6: Postman은 "P0 외 API 확인용" | 기능마다 Postman도 만든다. pytest 대상은 그대로 | **지금 상태 유지.** pytest 필수 대상 그대로, Postman은 그 외 확인용. tasks.md D6-01·D7-02 컬렉션 산출물은 그대로 만든다. 문서 수정 없음 | CLAUDE.md, CONSTITUTION 0-6 |
| 10 | 새 산출물 | 가이드의 verify.md·스펙 변경 이력·일일 개발 로그·보고서·사용자 매뉴얼·회고서가 문서에 없음 | tasks.md §5 문서 산출물 표대로 담당·위치 확정 | 제안대로 (tasks.md §5 표 확정) | tasks.md §5 |
| 11 | 산출물 파일명 | 가이드: spec.md · plan.md · data-model.md · api-contract.md. 우리: SPEC.md · ARCHITECTURE.md · DATABASE-DESIGN.md · API-SPEC.md | 이름은 그대로 두고 README에 대응표 | 제안대로 (README 대응표) | README |
| 12 | "v1.0" 두 가지 | 스펙 v1.0(11/13, M1)과 저장소 v1.0 태그(11/26) | 스펙은 문서 버전, 저장소는 git 태그로 구분 | 제안대로 | CONSTITUTION 변경 기록 |
| 13 | `/api/health` | ARCHITECTURE §8·tasks.md T-F0-04에는 있으나 API-SPEC §3 목록에 없음. CONSTITUTION 6-1 "인증 없이 호출할 수 있는 API는 회원가입과 로그인뿐"과 충돌 | API-SPEC §3에 `GET /health`(인증 없음, 데이터 없음) 추가 + CONSTITUTION 6-1에 예외 한 줄. 또는 health를 빼고 `/docs`로 확인 | 제안 앞쪽 채택: API-SPEC §3에 `GET /health` 추가 + CONSTITUTION 6-1 예외 | API-SPEC §3, CONSTITUTION 6-1 |
| 14 | 스펙 v1.0 동결 (D4-02) | 모든 문서가 v0.x. PROPOSAL·PROJECT-OVERVIEW에는 버전 표시가 없음 | 회의 결정 반영 후 전 문서 v1.0, 머리말 형식 통일, 동결 후 변경 절차(변경 이력 + 팀장 승인) 확정 | 제안대로 (2026-11-16 v1.0 동결) | 전 문서 머리말, CONSTITUTION |
| 15 | **DB 포트 3307 (이미 적용 — 11/16 확인 완료)** | 수업 PC에 MariaDB가 설치돼 3306을 쓰고 있어 `docker compose up`이 포트 충돌로 실패. 11/13 서승범이 PC 쪽 포트를 3307로 바꿈(컨테이너 안은 3306). 기능·API 변경 없음 | 3307 유지. 팀원 PC에서 3307이 비어 있는지 확인 | 제안대로 3307 유지. 팀원 PC 3307 사용 여부는 각자 확인 | 적용됨: `docker-compose.yml`, `.env.example`, ARCHITECTURE §1·§6, DATABASE-DESIGN §10, README |
| 16 | **패키지 목록 한 파일로 (이미 적용 — 11/16 확인 완료)** | ARCHITECTURE §2는 `requirements.txt`(실행)·`requirements-dev.txt`(개발) 두 파일. 어차피 4명 모두 처음에 둘 다 설치하므로 11/13 서승범이 `requirements.txt` 하나로 합침(실행용·개발용 구역으로 나눠 표시) | 한 파일 유지. 배포 때 개발 도구를 빼야 하면 그때 다시 나눔 | 제안대로 한 파일 유지 | 적용됨: `requirements.txt`, ARCHITECTURE §2, README, tasks.md T-F0-03 |

## 2. 회의 없이 처리할 것

결정이 필요 없고 문서와 파일을 맞추기만 하면 되는 항목이다.

| 항목 | 다른 점 | 담당 |
| --- | --- | --- |
| `.env.example` ✅ 처리됨(T-F0-03, 11/13) | 이전 `DB_HOST`·`DB_PORT`·`DB_USER=root`·`DB_PASSWORD`·`DB_NAME=Doing_It`·`JWT_SECRET`·`ALGORITHM`. ARCHITECTURE §6은 `MARIADB_ROOT_PASSWORD`, `MARIADB_USER`·`MARIADB_PASSWORD`(전용 계정 `doingit`), `DATABASE_URL`(스키마 `doing_it`), `TEST_DATABASE_URL`, `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `FRONTEND_ORIGIN`. `ALGORITHM`은 HS256 고정(API-SPEC §1.2)이라 키 불필요 | 서승범 (T-F0-03) |
| `requirements.txt` ✅ 처리됨(T-F0-03, 11/13) | SQLAlchemy·Alembic·PyMySQL·PyJWT·bcrypt 없음. 개발용(pytest·httpx·ruff·black) 없음 → 한 파일에 실행용·개발용 함께 (안건 16) (ARCHITECTURE §2). ※ `opentelemetry-api`는 FastAPI 0.162가 함께 설치하는 하위 패키지라 그대로 둔다(처음 점검 때 "스택 밖 패키지"로 잘못 적었던 것을 정정) | 서승범 (T-F0-03) |
| 저장소 구조 (일부 처리: `docker-compose.yml`·`init.sql` 11/13. `/api/health`는 안건 13으로 API-SPEC에 추가) | `backend/`·`frontend/`·`docker-compose.yml`·`docker/mariadb/init.sql`·`postman/` 아직 없음 (ARCHITECTURE §3) — 세팅 예정이라 정상 | T-F0-02~05 담당자 |
| Figma 누락 화면 | UI-DESIGN 머리말 "화면 6장". UI-DESIGN S1~S8 중 로그인·회원가입·설정·403/404 프레임 없음 | 김서현 (D4-05) |
| 표기 보충 (경미) ✅ 처리됨(11/16 v1.0 동결 때) | USER-STORIES US-07 제목에 `PRJ-07` 없음. API-SPEC `GET /projects/{project_id}`에 US 번호 없음 (SPEC §4는 PRJ-07 → US-07) | 안건 14 동결 때 함께 |

## 3. 점검 결과 — 서로 맞는 것

**점검 방법:** 각 문서에서 기능 ID·US 번호·오류 코드·버전 참조를 뽑아 대조했다. SPEC 시나리오는 개수를 직접 셌고, ARCHITECTURE §2·§3·§6은 저장소 파일과 비교했다.

| 항목 | 결과 |
| --- | --- |
| 기능 ID | 38개(P2·ADM-01 포함)가 REQUIREMENTS · SPEC · USER-STORIES에서 같다 |
| API ↔ 기능 ID ↔ US | API-SPEC §3·§5·§6의 근거 ID·US 번호가 USER-STORIES와 맞다. DASH-01·TASK-07은 §8에 기존 API 확장으로 정의돼 있다 |
| 오류 코드 | 다른 문서에 나온 오류 코드는 모두 API-SPEC §2 목록에 있다 |
| 상호 참조 버전 | REQUIREMENTS v0.8 · USER-STORIES v0.7 · DATABASE-DESIGN v0.6 · API-SPEC v0.4 · UI-DESIGN v0.2 — 참조하는 문서들이 모두 같은 값을 적었다 |
| SPEC 시나리오 | §11 표의 84개와 본문 시나리오 수가 같고 중복 ID가 없다 |
| 일정 게이트 | 11/19 P0 완료 게이트가 PROPOSAL · REQUIREMENTS · PRD · PROJECT-OVERVIEW · README에서 같다 |
| 주요 화면 | 7개(로그인·회원가입, 프로젝트 목록, 칸반, 업무 상세, 설정, 통계, 내 대시보드)가 REQUIREMENTS §6과 PRD에서 같다 |
| 쓰지 않는 패키지 | passlib · python-multipart · tzdata 등 ARCHITECTURE §2와 CLAUDE.md가 같다 |

## 4. 회의 후 할 일

1. ✅ 1장 결정 칸을 채운다. (11/16)
2. ✅ 안건별 "고칠 곳" 문서를 고친다. (11/16) 남은 일은 브랜치·PR로 올리는 것이다(안건 하나 또는 문서 하나에 PR 하나).
3. ✅ 바꾼 내용을 스펙 변경 이력([SPEC-CHANGELOG.md](./SPEC-CHANGELOG.md) #1)에 적는다.
4. ✅ tasks.md §9가 이 문서를 가리키도록 줄인다.
5. ✅ 이 문서를 v1.0으로 올린다.

**문서 밖에서 할 일**
- 서승범에게 GitHub 관리 권한(병합·브랜치 보호)을 준다. (안건 3)
- 팀원 각자 PC에서 3307 포트가 비어 있는지 확인한다. (안건 15)
- 강의 가이드의 Postman F1~F4 컬렉션은 tasks.md D6-01·D7-02대로 만든다. 문서 변경은 없다. (안건 9)
