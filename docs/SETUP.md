# 개발 환경 세팅 안내 (SETUP.md)

> 대상: 팀원 전원 · 수업 PC(Windows, VS Code 터미널 = PowerShell) 기준 | 작성일: 2026-11-16 | 문의: 가상환경 담당
> 걸리는 시간: 약 15분. 막히면 맨 아래 "막히면" 표를 먼저 본다.

| 누가 | 어디까지 |
| --- | --- |
| 백엔드 (양준석·서승범) | 0 ~ 4 전부 |
| 프론트 (최진영·김서현) | 0 ~ 2 (백엔드를 직접 띄워 보고 싶으면 3·4도) |

## 0. 최신 코드 받기 + 준비 확인

저장소 폴더에서 실행한다.

```powershell
git pull
docker --version
py -3.12 --version
```

버전이 안 나오면 먼저 설치한다.

| 프로그램 | 버전 |
| --- | --- |
| Docker Desktop | 최신 |
| Python | **3.12** (`py -0p`로 설치된 버전 목록 확인) |
| Node (프론트) | 22 LTS |

## 1. `.env` 만들기

```powershell
Copy-Item .env.example .env
```

- `.env`는 **Git에 올리지 않는다**(`.gitignore`에 있음).
- `change-me`를 각자 비밀번호로 바꿔도 된다. 바꾸면 `DATABASE_URL`·`TEST_DATABASE_URL` 안의 비밀번호도 **같이** 바꾼다.
- `JWT_SECRET_KEY`는 아래 명령 결과를 붙여 넣는다. DB 확인만 할 때는 비워 둬도 된다.
  ```powershell
  py -3.12 -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

## 2. DB 띄우기 (MariaDB, Docker)

Docker Desktop을 먼저 켜 둔다.

```powershell
docker compose up -d --wait
docker compose ps
```

- STATUS에 `healthy`가 보이면 성공이다. 처음 한 번은 이미지를 받느라 1~3분 걸린다.
- PC 쪽 포트는 **3307**이다. 수업 PC에 설치된 MariaDB가 3306을 쓰기 때문이다. 컨테이너 안은 3306 그대로다.
- 끄기: `docker compose stop` (데이터 유지) · 다시 켜기: `docker compose start`

## 3. 가상환경 + 패키지 설치

```powershell
py -3.12 -m venv .venv            # 처음 한 번만
.venv\Scripts\Activate.ps1        # 켜기 — 프롬프트 앞에 (.venv)가 붙으면 성공
python -m pip install --upgrade pip
pip install -r requirements.txt   # 실행용 + 개발용(pytest·httpx·ruff·black) 전부
```

- 터미널을 **새로 열 때마다** `.venv\Scripts\Activate.ps1`을 다시 실행한다.
- VS Code: `Ctrl+Shift+P` → "Python: Select Interpreter" → `.venv`를 고르면 새 터미널에서 자동으로 켜진다.
- 패키지를 새로 추가하지 않는다. 목록에 없는 라이브러리는 팀 합의가 필요하다(CONSTITUTION §5). `requirements.txt`는 서승범만 수정한다(tasks.md §3).
- `.venv` 폴더는 Git에 올라가지 않는다.

## 4. DB 접속 확인

```powershell
python -c "from dotenv import dotenv_values; from sqlalchemy import create_engine, text; v=dotenv_values('.env'); [print(k, create_engine(v[k]).connect().execute(text('SELECT DATABASE()')).scalar()) for k in ('DATABASE_URL','TEST_DATABASE_URL')]"
```

아래 두 줄이 나오면 끝이다.

```
DATABASE_URL doing_it
TEST_DATABASE_URL doing_it_test
```

## 막히면

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| Activate 할 때 "이 시스템에서 스크립트를 실행할 수 없으므로…" | Windows 기본 보안 설정 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` 한 번 실행 후 다시 Activate |
| `.env에 MARIADB_…를 넣어 주세요` | `.env` 파일이 없음 | 1번 다시 |
| `port is already allocated` / 3307 사용 중 | 그 PC에서 다른 프로그램이 3307을 씀 | 가상환경 담당에게 알리기 |
| `Access denied for user 'doingit'` | `.env` 비밀번호를 바꿨는데 DB는 예전 비밀번호로 이미 만들어짐 | `docker compose down -v` 후 2번부터 다시 (**DB 데이터가 지워짐** — 지금은 테이블이 없어서 괜찮다) |
| `docker: command not found` / 연결 오류 | Docker Desktop이 꺼져 있음 | Docker Desktop 실행 후 1분 기다리기 |
| `pip install` 실패 | 가상환경 Python이 3.12가 아님 | `.venv` 폴더를 지우고 `py -3.12 -m venv .venv`부터 다시 |
| `ModuleNotFoundError: No module named 'dotenv'` 등 | 가상환경이 꺼진 상태에서 실행 | `.venv\Scripts\Activate.ps1` 후 다시 |

다 되면 팀 채팅에 "4번 성공" 또는 "N번에서 막힘 + 오류 문구"를 남긴다.
