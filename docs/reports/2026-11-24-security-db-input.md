# 보안 점검 — DB·입력값 (D10-03)

> 프로젝트: 동잇(Doing_It) | 점검: 서승범 | 작성일: 2026-11-24 (Day 10)
> 기준: main `3acea1e` · 테스트 DB `doing_it_test`(마이그레이션 `0003`) · 근거: CLAUDE.md §5, API-SPEC §1·§5·§6, DATABASE-DESIGN §2·§4
> 보안 점검 체크리스트(취합: 양준석)에 넣을 서승범 몫이다. 인증·권한은 양준석, XSS·토큰 노출·`/dev/components`는 최진영이 맡는다. 명세가 아니며, 명세와 다르면 명세를 따른다.

## 1. 요약

| 구분 | 결과 |
| --- | --- |
| 점검 항목 | 19개 (정적 11 · 동적 8) |
| ✅ 통과 | 16 |
| ❌ 실패 | **1** — `page`가 아주 크면 목록 API 7개가 500 (§3 D-2, 이슈 #142) → **11/24 해결**(`4ec8d3c`, page 상한 1,000,000 → 422) |
| ⚠️ 주의 | 2 — DB 포트가 모든 네트워크에 열림, 검색어 길이 제한 없음 |
| 회귀 테스트 | `backend/tests/test_security_input.py` 60개 → 점검 당시 57 통과 + 알려진 실패 3개(`xfail`). #142 수정 뒤 `xfail` 표시를 지워 **60개 모두 통과**, 전체 pytest **464 passed**(main `5e18360`) |

- **SQL 주입 경로는 찾지 못했다.** 모든 쿼리가 ORM 식과 바인딩 파라미터를 쓰고, LIKE 검색은 와일드카드를 글자 그대로 처리한다.
- 동적 점검은 테스트 DB에서만 했다. 개발 DB(시연 데이터)는 건드리지 않았다.

## 2. 정적 점검 (코드·DB 메타데이터)

| # | 항목 | 방법 | 결과 | 근거 |
| --- | --- | --- | :-: | --- |
| S-1 | 사용자 입력을 SQL 문자열에 이어 붙이는 곳 | `backend/app·core·scripts`에서 f-string SQL·`.format`·`%s`·`text(` 검색 | ✅ | 0곳. `.format`은 오류 문구(`core/exceptions.py:111`), `%s`는 로그(`:167`)뿐. 원시 SQL·`text()`는 상수 2곳(`core/db.py:28` `SET time_zone`, `models/user.py:38` `server_default=text(1)` 형태의 상수)이고 사용자 입력이 없다 |
| S-2 | `db.execute` 직접 호출 | 6곳 열어 확인 | ✅ | `activity_service.py:153`, `member_service.py:45`, `project_service.py:43·100`, `stats_service.py:38·135` 모두 `select(...)` 식 |
| S-3 | LIKE 와일드카드 | `contains·like·ilike` 검색 | ✅ | `task_service.py:143` `contains(q, autoescape=True)` 1곳뿐 |
| S-4 | 요청 본문의 정의 안 된 필드 | 요청 스키마 11개 `model_config` | ✅ | 11개 모두 `extra="forbid"` (가입·로그인·이름 수정·프로젝트 생성/수정·멤버 추가/역할·업무 생성/수정·댓글 작성/수정) |
| S-5 | 문자열 최대 길이(DB TEXT 한도 500 재발 방지) | 스키마 필드 제약 | ✅ | 이름 50·비밀번호 64(72바이트)·프로젝트 이름 30·설명 2000·업무 제목 30·업무 설명 2000·댓글 300. 로그인 아이디·비밀번호와 멤버 추가 아이디는 조회에만 써서 제한 없음(명세: 로그인은 형식이 틀려도 401) |
| S-6 | 검색어 `q` 길이 | `TaskFilter` | ⚠️ | 제한 없음(`schemas/task.py:44`). 제목이 30자라 긴 검색어는 결과 0건이고 500도 나지 않는다. URL 길이 한도가 사실상 상한이다. P2 후보: `max_length` 추가 |
| S-7 | 응답의 `password_hash` | 응답 스키마·라우터 검색 | ✅ | 응답 모델에 없음(`schemas/auth.py` `UserOut`). 결과서 AUTH-03-a도 확인 |
| S-8 | 비밀 값 관리 | `git ls-files`, `.env.example`, `core/config.py` | ✅ | 저장소의 `.env` 계열은 `.env.example`뿐이고 `JWT_SECRET_KEY`는 빈 값이다. 서버는 키 최소 길이를 강제한다(`config.py:43`). 값은 출력하지 않았다 |
| S-9 | 문자셋 | `information_schema.TABLES·COLUMNS` | ✅ | 테이블 7개 `utf8mb4_unicode_ci`, utf8mb4가 아닌 컬럼 0개. 상태·역할·`login_id` 컬럼 7개는 `utf8mb4_bin`(DATABASE-DESIGN v1.2) |
| S-10 | DB 제약 = 설계 | `CHECK_CONSTRAINTS`·`STATISTICS`·`REFERENTIAL_CONSTRAINTS` | ✅ | CHECK 14개·UNIQUE 2개가 DATABASE-DESIGN과 이름까지 같다(P2 체크리스트 제외). FK 11개 삭제 규칙(CASCADE·SET NULL·RESTRICT)이 §5 표와 같다. MariaDB ENUM 컬럼 0개 |
| S-11 | DB 포트 노출 | `docker-compose.yml` | ⚠️ | `"3307:3306"`(22행) → PC의 모든 네트워크 인터페이스에 열린다. 발표 PC가 공용 Wi-Fi에 있으면 같은 망에서 개발용 비밀번호로 접속을 시도할 수 있다. 제안: `"127.0.0.1:3307:3306"`(기능 영향 없음, 팀장 확인 후) |

## 3. 동적 점검 (`backend/tests/test_security_input.py`)

| # | 항목 | 입력 | 결과 | 테스트 |
| --- | --- | --- | :-: | --- |
| D-1 | 아주 큰 경로 id | 프로젝트·업무 목록·업무·댓글·멤버 경로 × `2^63`·`10^30`·4301자리·`-1`·`0` | ✅ | `test_huge_path_id_not_500` (25개) → 4301자리는 422(정수 변환 단계), 나머지는 404 |
| D-2 | `page`·`size` 범위 | `10^30`·`-1`·`0`·`abc`, `page` 1.9×10^17 + `size=100` | **❌ → ✅** | `test_page_size_out_of_range_422` — `size` 4개와 `page` 3개(`-1`·`0`·`abc`)는 422. **`(page-1)×size`가 약 1.8×10^19를 넘으면 500** → 아래 §4 |
| D-3 | 본문의 아주 큰 정수 | 업무 등록 `assignee_id` = `2^63`·`10^30` | ✅ | `test_huge_assignee_id_in_body_not_500` → 400·422 |
| D-4 | 검색어의 SQL·와일드카드 | `' OR 1=1 --`·`%`·`_`·`50%_`·`\`·`/`(이스케이프 문자)·없는 말 | ✅ | `test_search_q_sql_and_wildcards_literal` → 제목 `50%_할인`·`c\d`·`a/b`·`일반` 중 글자 그대로 일치하는 것만 |
| D-5 | SQL처럼 생긴 값 저장 | 제목 `'; DROP TABLE tasks; --` | ✅ | `test_sql_like_title_stored_literally` → 201, 값 그대로, 업무 1개 |
| D-6 | 널 바이트·4바이트 이모지 | 업무 제목·댓글·이름 × `a\x00b`·`😀`×30·ZWJ 이모지 | ✅ | `test_null_byte_and_emoji_round_trip` → 201·201·200으로 저장되고 같은 값으로 돌아옴(글자 깨짐·500 없음). 널 바이트를 거절할지는 명세에 규칙이 없어 지금 동작을 고정만 했다 |
| D-7 | 정의 안 된 필드 끼워 넣기 | 가입 `system_role`, 업무 `created_by`·`project_id`·`id`·`completed_at`, 프로젝트 `my_role`, 댓글 `user_id` | ✅ | `test_signup_system_role_rejected` 외 3개 → 모두 422. 사용자·업무·댓글 0행, 프로젝트 이름 그대로 |
| D-8 | JSON이 아닌 본문·틀린 타입 | 깨진 JSON·배열·객체·숫자·문자열 | ✅ | `test_non_json_and_wrong_types_422` → 422 `VALIDATION_ERROR` |

- 변이 확인(테스트가 진짜 잡는지 보려고 코드를 잠깐 망가뜨림 → 되돌림):
  - `autoescape=True`를 빼면 D-4 3개 실패(`%`·`_`·`\`)
  - `TaskCreate`의 `extra="forbid"`를 `ignore`로 바꾸면 D-7 4개 실패, `CommentCreate`도 바꾸면 댓글 1개 실패
  - `page`에 상한을 넣으면 D-2의 `xfail` 3개가 XPASS로 실패 → 고친 뒤 표시를 지우라는 신호. `xfail`은 `raises=ProgrammingError`라 다른 이유의 실패는 흡수하지 않는다
  - D-1은 별도 검증 코드 없이 정수 변환 + DB 조회로 404가 나는 구조라, 성립하는 변이가 없다. 대신 상태 코드를 하나로 정해 단정한다

## 4. ❌ D-2: `page`가 아주 크면 목록 API 500 — 11/24 해결

- **증상:** `OFFSET = (page-1)×size`가 MariaDB 한도(2^64-1 ≈ 1.8×10^19)를 넘으면 → `1064 SQL syntax ... near '19999999999999999980, 20'` → 500. 응답에는 공통 예외 처리로 내부 정보가 나가지 않는다(`INTERNAL_ERROR`).
  - `size=20`(기본): `page=922337203685477581`까지 200, `923000000000000000`부터 500
  - `size=100`: `page=184467440737095516`까지 200, `190000000000000000`부터 500
- **범위:** `PageParams`를 쓰는 목록 API 7개 모두
  - `/projects`
  - `/projects/{id}/tasks`
  - `/projects/{id}/members`
  - `/tasks/{id}/comments`
  - `/tasks/{id}/activities`
  - `/projects/{id}/activities`
  - `/users/me/tasks`
- **원인:** `core/pagination.py:24` `page`가 `ge=1`만 있고 위쪽 한도가 없다. `OFFSET = (page-1)×size`가 MariaDB 정수 범위를 넘어 SQL이 거절된다.
- **영향:** 데이터 노출·변경은 없다. 잘못된 입력에 500이 나는 무결성 문제이고, 서버 오류 로그가 쌓인다.
- **제안(코드는 `core/` 담당 양준석):** `page`에 상한을 둔다(예: `le=10**6` → 422). API-SPEC §1.3에 "page 상한"을 한 줄 더한다.
  - 고치면 `test_page_size_out_of_range_422`의 `xfail` 표시 3개를 지운다(남겨 두면 strict라 실패로 알려 준다).
- **처리:** 이슈 #142 → 양준석.
- **해결(11/24):** `4ec8d3c fix(NFR-05): 목록 API page 상한 추가` — `core/pagination.py` `MAX_PAGE = 1_000_000`(`le=MAX_PAGE`), API-SPEC §1.3 `page` 1~1,000,000(v1.11, SPEC-CHANGELOG #34). 같은 커밋에서 `xfail` 표시 3개를 지웠고, 세 케이스는 이제 422로 통과한다. 재확인: `test_security_input.py` 60 passed(서승범, main `5e18360`).

## 5. 범위 밖 · 참고

- 인증·권한(JWT, 403 매트릭스)은 양준석, XSS·토큰 노출·`/dev/components` 배포 제외는 최진영 점검 범위다.
- 11/23에 알려진 P2 후보는 다시 적기만 한다: 폭 없는 공백(`​`)만 있는 이름·댓글이 통과한다(가입·이름 수정·댓글 공통, 명세에 규칙 없음).
- 토큰 없이 깨진 JSON을 보내면 401이 아니라 422다. FastAPI가 본문을 먼저 읽는 동작이고 모든 본문 API에 공통이다(11/23 #116 리뷰).
- 요청 본문 크기 상한·요청 횟수 제한(DoS)은 로컬 시연 범위라 점검하지 않았다.
- 정수 필드는 Pydantic 기본(느슨한) 변환이라 본문 `assignee_id`에 `true`·`"1"`·`1.0`을 보내도 1로 받는다. 멤버 검사(400)는 그대로 적용돼 권한 우회는 아니다. P2 후보: `StrictInt` (11/24 리뷰 확인).
- 리뷰 중 추가로 시도해 500이 없던 것: 필터 `assignee_id` 19자리(BIGINT 초과) → 200·0건, 마감일 `0001-01-01`·`9999-12-31`(필터·등록·대시보드) → 200·201, `10000-01-01` → 422, `q` 7000자 → 200, 멤버 추가 아이디 10만 자·널 바이트 → 404, 로그인 10만 자 → 401.
