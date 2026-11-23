# Postman 컬렉션

P0 핵심 API는 pytest로 확인하고, 실제 서버에 띄워서 확인할 때와 시연 리허설에는 이 컬렉션을 쓴다(CONSTITUTION 3-1).

## 파일
| 파일 | 범위 | 담당 |
| --- | --- | --- |
| `local.postman_environment.json` | 공통 환경: `baseUrl = http://localhost:8000/api` | 양준석 |
| `F1-auth.postman_collection.json` | 회원가입·로그인·내 정보 | 양준석 |
| `F2-projects.postman_collection.json` | 프로젝트 생성·목록·상세·수정·삭제 | 양준석 |
| `F2-tasks.postman_collection.json` | 업무 등록·목록·상세·수정·삭제 — 권한별 허용·403, 400·422 검증 (사용자 4명: OWNER·작성자·담당자·비멤버) | 김서현 |
| `F3-members.postman_collection.json` | 멤버 목록·추가·제거 — OWNER 먼저 정렬, 403(MEMBER·비멤버)·404·409·400·422, 제거 후 담당 해제·목록에서 사라짐 확인 (사용자 5명: OWNER 2·MEMBER·제거 대상·비멤버) | 양준석 |
| `F4-comments-activities.postman_collection.json` | 댓글 작성·목록·수정·삭제, 업무 이력·프로젝트 최근 활동 — 작성자만 수정·삭제(OWNER도 403)·비멤버 403·404·422 경계값(300/301자), 이력 최신순·항목마다 1행·삭제된 업무 이력 (사용자 3명: OWNER·MEMBER·비멤버) | 김서현 |

- 영역마다 파일을 나눈다. 한 파일을 둘이 고치면 JSON 충돌이 난다.
- 비밀 값(토큰·비밀번호)은 환경 파일에 넣지 않는다. 토큰은 로그인 요청이 실행 중에 컬렉션 변수로 저장한다.
- 실행할 때마다 새 아이디로 가입하므로 몇 번을 돌려도 된다. 시드 데이터와 섞이지 않는다.

## 실행
백엔드 서버(8000)를 켠 뒤 둘 중 하나로 실행한다.

- **Postman 앱:** Import → `postman/` 파일 6개 선택 → 오른쪽 위 환경을 `동잇 로컬`로 → 컬렉션 Run
- **Postman CLI:**
  ```
  postman collection run postman/F1-auth.postman_collection.json -e postman/local.postman_environment.json
  postman collection run postman/F2-projects.postman_collection.json -e postman/local.postman_environment.json
  postman collection run postman/F2-tasks.postman_collection.json -e postman/local.postman_environment.json
  postman collection run postman/F3-members.postman_collection.json -e postman/local.postman_environment.json
  postman collection run postman/F4-comments-activities.postman_collection.json -e postman/local.postman_environment.json
  ```

## 새 컬렉션 만들 때
- 요청마다 상태 코드와 `code`를 확인하는 Tests 스크립트를 넣는다. 권한이 있는 API는 403 실패 케이스를 꼭 넣는다.
- 위에서부터 순서대로 실행해도 통과하게 만든다(필요한 사용자·프로젝트는 컬렉션 안에서 만든다).
- 환경은 `local.postman_environment.json` 하나를 같이 쓴다.
