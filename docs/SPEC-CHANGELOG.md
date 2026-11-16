# 스펙 변경 이력 (SPEC-CHANGELOG.md)

> 프로젝트: 동잇(Doing_It) | 시작: 2026-11-16 (스펙 v1.0 동결) | 산출물 D6-03
> 스펙 v1.0 동결 후 명세를 바꾸는 절차는 CONSTITUTION 1-4를 따른다.
> 1. **바꾼 사람**이 이 표에 직접 한 줄을 적는다.
> 2. 팀장(양준석)이 승인한다. 팀장이 없으면 예비 팀장(서승범)이 승인하되, 명세 수정 결정(API·범위 변경)은 "팀장 확인 필요"로 남기고 미룬다(CONSTITUTION 3-5).
> 3. 같은 PR에서 해당 문서의 버전(v1.1 …)과 머리말을 올린다.
>
> 이력은 최신순으로 적는다. 이력 하나가 문서 여러 개를 고치면 같은 번호를 쓴다.

| # | 날짜 | 문서 (버전) | 바꾼 내용 | 이유 | 바꾼 사람 | 승인 |
| :-: | --- | --- | --- | --- | --- | --- |
| 4 | 2026-11-16 | DATABASE-DESIGN §1-7·§4 (v1.2) | 상태·역할 컬럼 6개(`users.system_role`, `project_members.role`, `tasks.status`·`priority`, `task_activities.action`·`field`)를 `COLLATE utf8mb4_bin`으로 바꿈. §4 공통 규칙에 이유 추가 | 기본 `_ci` 콜레이션에서는 `'todo'`·`'owner'` 같은 소문자 값이 CHECK를 통과함. CONSTITUTION 8-4(DB로 막을 수 있으면 DB에서). 0001 병합 전이라 지금 고치는 비용이 가장 낮음 (T-F0-07 코드 리뷰 지적) | 서승범 | 팀장 확인 필요 |
| 3 | 2026-11-16 | DATABASE-DESIGN §4.5 (v1.1) | `ck_task_activities_field`의 UPDATED 조건에 `field IS NOT NULL` 추가. 설계 의도(UPDATED면 field가 4개 중 하나)는 그대로 | 기존 식은 `NULL IN (...)`이 "알 수 없음"이 되어 `UPDATED` + `field = NULL` 행이 CHECK를 통과함 (T-F0-07 구현 중 실제 MariaDB에서 확인) | 서승범 | 팀장 확인 필요 |
| 2 | 2026-11-16 | TASKS (v1.1), README, CONSTITUTION·ARCHITECTURE·PROPOSAL·UI-DESIGN·SETUP·CONSISTENCY-CHECK 참조 | `tasks.md` → `TASKS.md` 파일명 통일. 다른 문서 참조 수정, 내용 변경 없음 | 다른 docs 문서와 대문자 파일명 통일 | 양준석 | 팀장 확인 필요 |
| 2 | 2026-11-16 | CONSTITUTION 10-2 (v1.1), TASKS D5-01·§8-7, CLAUDE.md | 개발 로그 파일명을 `docs/devlog/<영문이름>.md` → `docs/devlog/<한국이름>.md`로 바꾸고 파일명 영어 규칙에 예외 추가 | 팀원이 자기 파일을 바로 찾도록 | 양준석 | 팀장 확인 필요 |
| 2 | 2026-11-16 | ARCHITECTURE §3·§8 (v1.1), CLAUDE.md §4 | 저장소 구조에 `requirements.txt`·`.github/`·`docs/devlog/`·`verify.md`·`reports/`·`USER-MANUAL.md` 위치 추가. §8에 compose·init.sql 11/13 완료 표시 | TASKS §5 산출물 위치와 실제 파일에 맞춤 | 양준석 | 팀장 확인 필요 |
| 2 | 2026-11-16 | TASKS §4·§5 (v1.1) | D4-01(서승범 대신 작성)·D4-02 완료일 11/16 반영, T-F0-04·05 "마감 지남" 표시 | 실제 진행과 맞춤 | 양준석 | 팀장 확인 필요 |
| 2 | 2026-11-16 | CLAUDE.md §6, README | 리뷰어 규칙(조 안 고정 + `core/`·마이그레이션 같은 영역 리뷰어 추가)과 동결 후 변경 절차 한 줄 추가 | CONSTITUTION 3-2·1-4와 맞춤 (헌법 내용 변경 없음) | 양준석 | 팀장 확인 필요 |
| 1 | 2026-11-16 | 전 문서 → v1.0 | 스펙 v1.0 동결. 머리말 버전 칸 맨 앞에 `v1.0 (2026-11-16 스펙 동결…)`을 붙이고, 서로 참조하는 버전을 v1.0으로 맞춤. PROPOSAL·PROJECT-OVERVIEW에 버전 표시 추가. CONSTITUTION 1-4에 동결 후 변경 절차 추가 | 회의 안건 14 (M1) | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | CONSTITUTION, PROPOSAL §8, UI-DESIGN §2, ARCHITECTURE §8, PROJECT-OVERVIEW, README, CLAUDE.md | 역할을 TASKS.md 조 편성(A조 양준석·최진영 / B조 서승범·김서현)에 맞춤. 대시보드 API(DASH-01·03·04)는 BE-A로, 진행률·통계·내 대시보드 화면은 FE-A로, 403·404 화면은 FE-B로 옮김. TASKS.md v1.0 채택 | 안건 1 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | CONSTITUTION 3-2, PROPOSAL §8 | 리뷰 방식을 "돌아가며"에서 "조 안 영역 교차 고정 리뷰 + `core/`·마이그레이션은 같은 영역 리뷰어 추가"로 바꿈 | 안건 2 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | CONSTITUTION 3-5 | 팀장이 없을 때 예비 팀장(서승범)이 대행하는 범위 추가. 명세 수정 결정은 미룸 | 안건 3 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | PROPOSAL §7, USER-STORIES 스프린트 배치, PROJECT-OVERVIEW, README, CLAUDE.md | 일정 변경: 11/13은 설계 마감·개발 환경, 코딩은 11/16 시작. P0는 11/16~11/19 오전(F1·F2는 11/17까지, 11/18 오전 버퍼). P1은 11/19 오후~11/23(1순위 6개). 11/24 검증·기능 동결. 합계 92h 유지 | 안건 4·5·7 (과정 가이드 기준) | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | REQUIREMENTS §7.1, PRD | P1 일정을 "11/19 오후~11/23, 11/24 기능 동결"로 명시 | 안건 7 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | API-SPEC §1.2·§9, CONSTITUTION 6-1, CLAUDE.md | 인증 헤더를 OAuth2 Bearer 규격(RFC 6750)으로 명시. FastAPI `HTTPBearer(auto_error=False)`로 읽고, 헤더가 없거나 틀리면 401 `UNAUTHORIZED`. 로그인은 JSON 그대로이며 폼 로그인·`python-multipart`는 쓰지 않음 | 안건 8 (가이드 6일차 "JWT·OAuth2") | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | API-SPEC §1.2·§3·§9, CONSTITUTION 6-1, CLAUDE.md | `GET /api/health` 추가. 인증 없이 200 `{ "status": "ok" }`만 돌려주며 DB 조회와 데이터는 없음. 인증 예외 문구 추가 | 안건 13 (T-F0-04가 쓰는 API가 명세에 없었음) | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | ARCHITECTURE §2 | `requirements.txt` 한 파일(안건 16)과 DB 포트 3307(안건 15)을 확정하고 "팀장 확인 필요" 표기 삭제 | 안건 15·16 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | README | 과정 가이드 산출물 이름(spec.md·plan.md·data-model.md·api-contract.md·tasks.md)과 우리 문서의 대응표 추가 | 안건 11 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | CONSTITUTION 1-4·변경 기록 | "스펙 v1.0"은 문서 버전, "저장소 v1.0"은 11/26 git 태그로 구분 | 안건 12 | 11/16 회의 | 전원 합의 |
| 1 | 2026-11-16 | USER-STORIES US-07, API-SPEC §3 | US-07 제목에 `PRJ-07`을, `GET /projects/{project_id}`에 US-07을 표기 | 표기 보충 (CONSISTENCY-CHECK 2장) | 11/16 회의 | 전원 합의 |
