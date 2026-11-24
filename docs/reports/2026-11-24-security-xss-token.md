# 보안 점검 — XSS·토큰 노출 (D10-03)

> 프로젝트: 동잇(Doing_It) | 점검: 최진영 | 작성일: 2026-11-24 (Day 10)
> 기준: main `5e18360` · 개발 DB(점검 데이터는 검증용 프로젝트 12·13에만 넣음, 시연 프로젝트 4는 보기만 하고 수정하지 않음) · 근거: PROPOSAL 기술 스택 선정 기준(토큰 방식), CONSTITUTION 6-5·6-6, API-SPEC §1.2, ARCHITECTURE §5.3·§5.4, UI-DESIGN §6.5
> 보안 점검 체크리스트(취합: 양준석)에 넣을 최진영 몫이다. 인증·권한은 양준석, DB·입력값은 서승범(`2026-11-24-security-db-input.md`)이 맡는다. 명세가 아니며, 명세와 다르면 명세를 따른다.

## 1. 요약

| 구분 | 결과 |
| --- | --- |
| 점검 항목 | 30개 (정적 16 · XSS 화면 10 · 토큰 동작 4) |
| ✅ 통과 | 28 |
| ❌ 실패 | **0** |
| ⚠️ 주의 | 2 — 응답 보안 헤더 없음, 토큰을 localStorage에 둠(명세상 결정) |

- **XSS 경로는 찾지 못했다.** 사용자 입력은 모두 JSX 글자로만 출력되고, HTML로 해석하는 코드·라이브러리가 없다. 위험한 값을 넣은 업무·프로젝트·이름으로 화면 10곳을 확인했고 경고창은 한 번도 뜨지 않았다.
- **토큰 노출 경로는 찾지 못했다.** 토큰은 `/api` 요청의 `Authorization` 헤더로만 가고, 주소·콘솔·로그·Git 저장소에 남지 않는다. 로그아웃·만료 때 지워진다.

## 2. 정적 점검 (코드)

| # | 항목 | 방법 | 결과 | 근거 |
| --- | --- | --- | :-: | --- |
| S-1 | HTML로 출력하는 곳 | `frontend/src`에서 `dangerouslySetInnerHTML`·`innerHTML`·`outerHTML`·`insertAdjacentHTML`·`document.write`·`eval`·`new Function` 검색 | ✅ | 0곳. 금지 주석만 있음(`ToastProvider.jsx:89`, `TaskDetailModal.jsx:349`, `TaskComments.jsx:26` 등) |
| S-2 | HTML·마크다운 변환 라이브러리 | `package.json` | ✅ | 없음. 의존성은 React·React Router·Axios·Tailwind CSS뿐(모두 명세 기술 스택, ARCHITECTURE §2) |
| S-3 | 사용자 값을 `href`·`src`에 넣는 곳 | `href={`·`src={`·`window.open`·`location.*` 검색 | ✅ | 없음. 링크는 숫자 id로만 만든다(`/projects/:id/tasks/:taskId`). `javascript:` URL이 들어갈 자리가 없다 |
| S-4 | 서버 오류 메시지 출력 | 토스트 | ✅ | `message`를 글자로만 넣는다(`ToastProvider.jsx:89`) |
| S-5 | 말풍선(`title` 속성) | 달력 칩·간트 제목·막대 | ✅ | `MyTaskCalendar.jsx:253`, `GanttPage.jsx:374·418`. `title`은 브라우저가 HTML로 해석하지 않는다 |
| S-6 | 콘솔 출력 | `console.*` 검색 | ✅ | 0곳 → 토큰을 콘솔에 남기는 곳 없음 |
| S-7 | 토큰 저장 위치 | `core/api/client.js` | ⚠️ | localStorage `doingit_token` 한 곳(`client.js:3·7-9`). **명세상 결정**(CONSTITUTION 6-6, ARCHITECTURE §5.3). XSS가 생기면 읽힐 수 있는 위치라 S-1~S-5로 막는다 |
| S-8 | 토큰을 보내는 곳 | Axios 인터셉터 | ✅ | `Authorization: Bearer` 헤더로만(`client.js:17`). 401이면 지우고 로그인 화면으로(`client.js:28-32`, 로그인 요청의 401은 제외) |
| S-9 | 토큰이 주소에 들어가는 곳 | 라우터·`location` 검색 | ✅ | 없음. 만료 안내용 `/login?expired=1`만 있다 |
| S-10 | 토큰 내용·서명 | `backend/core/security.py` | ✅ | 담는 값은 `sub`(사용자 id)·`exp`뿐(`:37`). 검증 때 `algorithms=[HS256]`으로 고정해 `alg` 바꿔치기를 막는다(`:44-48`) |
| S-11 | 백엔드 로그 | `logger`·`print` 검색 | ✅ | 500 때 요청 방식·경로만 남긴다(`core/exceptions.py:167`). 헤더·토큰·본문은 남기지 않는다 |
| S-12 | 500 응답 내용 | 공통 예외 처리 | ✅ | "서버 오류가 발생했습니다"만 보낸다(`exceptions.py:169-170`). 내부 오류 내용 숨김 |
| S-13 | 저장소에 남은 실제 토큰 | 현재 파일 + 전체 이력에서 JWT 모양(`eyJ….….`) 검색 | ✅ | 0건. Postman은 `{{ownerToken}}` 같은 변수만 쓴다 |
| S-14 | CORS | `backend/app/main.py` | ✅ | `FRONTEND_ORIGIN` 하나만 허용, `allow_credentials=False`, 헤더는 `Authorization`·`Content-Type`만(`:42-46`) |
| S-15 | `/dev/components` 배포 제외 | `App.jsx`, 빌드 결과 | ✅ | `import.meta.env.DEV`일 때만 경로를 등록한다(`App.jsx:17-18`). `npm run build` 결과에 미리보기용 별도 파일(지연 로딩 조각)이 생기지 않는다(`dist/assets`에 `index` js·css만) |
| S-16 | 응답 보안 헤더 | 화면 T-1의 응답 헤더 | ⚠️ | `Content-Security-Policy`·`X-Content-Type-Options` 없음. 응답은 `application/json`이라 브라우저가 실행하지 않는다. 로컬 시연이라 영향은 작다. P2 후보 |

## 3. XSS 화면 점검

넣은 값(서버는 글자 그대로 저장 — 정상):

| 대상 | 값 | 위치 |
| --- | --- | --- |
| 업무 제목 | `<img src=x onerror=alert(1)>` | 프로젝트 12 업무 #28 (담당 박민호, 11/27 마감) |
| 업무 설명 | `<script>alert('xss')</script>` / `<a href="javascript:alert(2)">link</a>` | #28 |
| 댓글 | `"><svg onload=alert(3)>` | #28 댓글 #5 |
| 프로젝트 이름·설명 | `<img src=x onerror=alert(4)>` / `<script>alert(5)</script>` | 점검용 프로젝트 13 (업무 #33 박민호 담당) |
| 사용자 이름 | `"><svg onload=alert(6)>` | `seoyeon11` — 점검 뒤 원래 이름으로 되돌림 (업무 #34 담당자 변경·댓글 #6) |
| 검색어 | `<img` | 보드 검색창 → 새로고침 |

통과 기준: 경고창이 뜨지 않고, 넣은 값이 글자 그대로 보인다(이미지·링크·SVG가 생기지 않는다).

| # | 화면 | 확인한 곳 | 결과 |
| --- | --- | --- | :-: |
| D-1 | 내 대시보드 목록 | 업무 제목, 프로젝트 이름 | ✅ |
| D-2 | 내 대시보드 달력 | 칩 제목, 칩 말풍선(제목 · 프로젝트 이름) | ✅ |
| D-3 | 보드 | 카드 제목, 프로젝트 이름(머리), 담당자 아바타 | ✅ |
| D-4 | 보드 검색 | `<img` 입력 → 결과 카드 1개 → 새로고침해도 경고창 없음 | ✅ |
| D-5 | 업무 상세 | 제목, 설명(`link`가 링크로 바뀌지 않음), 댓글, 댓글 작성자, 담당자 | ✅ |
| D-6 | 업무 상세 변경 이력 | 담당자 변경 문장(사용자 이름 포함). 업무 제목은 이 탭에 나오지 않음 | ✅ |
| D-7 | 간트 | 왼쪽 제목, 제목 말풍선, 막대 말풍선(제목 · 기간 · 임박) | ✅ |
| D-8 | 통계 | 마감 임박 목록, 최근 활동(이력 속 업무 제목·삭제된 업무 제목), 담당자별 현황 | ✅ |
| D-9 | 프로젝트 목록·설정 | 카드 이름·설명, 설정 이름·설명, 멤버 목록 | ✅ |
| D-10 | 상단 바 | `seoyeon11` 로그인 시 이름(긴 이름은 말줄임) | ✅ |

## 4. 토큰 동작 점검 (브라우저 개발자 도구)

| # | 항목 | 방법 | 결과 |
| --- | --- | --- | :-: |
| T-1 | 토큰은 API 헤더로만 | 네트워크 탭 `Fetch/XHR` → `GET /api/projects/13/tasks?status=TODO…` 요청 헤더 | ✅ `Authorization: Bearer …` 있음. 주소에 토큰 없음. 보낸 곳 `[::1]:5173`(내 PC). 확인한 요청(API·웹소켓)은 모두 `localhost:5173` |
| T-2 | `링크 복사`에 토큰 없음 | 업무 상세 `링크 복사` → 붙여 넣기 | ✅ `http://localhost:5173/projects/4/tasks/6`처럼 주소만(`TaskDetailModal.jsx:152`, 보기만 해서 데이터 변경 없음) |
| T-3 | 로그아웃 때 토큰 삭제 | 애플리케이션 탭 → 로컬 저장소 → 로그아웃 | ✅ `doingit_token` 사라짐(`AuthContext.jsx:82`) |
| T-4 | 만료 토큰 처리 | 점검 중 만료 안내가 실제로 뜸(만료 2시간, AUTH-04-b) | ✅ `/login?expired=1` → "로그인이 만료되었습니다. 다시 로그인해 주세요"(UI-DESIGN §6.5). 401 때 토큰 삭제는 코드로 확인(`client.js:28-32`) |

- 네트워크 탭의 `websocket` 요청 `/?token=…`은 개발 서버(Vite)의 화면 자동 갱신 연결이 쓰는 자체 보호 값이다. 로그인 토큰(JWT)이 아니고, `npm run dev`에서만 생긴다(빌드에는 없음).

## 5. 범위 밖 · 참고

- 인증·권한(403 매트릭스)은 양준석, SQL·입력값 길이·`page` 상한(#142, #145로 수정됨)은 서승범 점검 범위다. `password_hash` 미포함·`.env` 관리(CONSTITUTION 6-7·6-8, NFR-02)는 서승범 S-7·S-8에서 다룬다.
- S-16(보안 헤더)·S-7(localStorage)은 로컬 시연 범위에서 받아들인 위험이다. 배포한다면 CSP 추가를 검토한다. 토큰 저장 방식(localStorage)은 PROPOSAL·CONSTITUTION 6-6의 결정이라, 바꾸려면 명세 변경이 먼저다.
- 점검 데이터는 검증용 프로젝트 12(#28~#32)·점검용 프로젝트 13(#33·#34)에 남겨 두었다. 사용자 이름은 원래대로 되돌렸다.
- 보안과 별개로 D-7(간트) 확인 중 화면 버그를 찾았다: 창 폭 약 960px 미만에서 간트 막대·오늘 선이 날짜 머리줄과 어긋난다(NFR-06). 이슈 #149로 등록 → 김서현.
