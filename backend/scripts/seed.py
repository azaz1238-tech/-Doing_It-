"""시연 데이터 넣기 (T-F0-10, DATABASE-DESIGN 시드, ARCHITECTURE §9).

실행 (backend 폴더에서, 개발 DB = .env의 DATABASE_URL):
    ..\\.venv\\Scripts\\python.exe -m scripts.seed

- 빈 DB에만 넣는다. 사용자가 한 명이라도 있으면 아무것도 넣지 않고 멈춘다(덮어쓰기 없음).
  다시 넣으려면 DB를 비운 뒤 실행한다(docs/SETUP.md "시연 데이터").
- 사용자 4명, 프로젝트 1개, 업무 12개(할 일 4 · 진행 중 3 · 완료 5, UI-DESIGN S4 예시와 같은 분포).
- 마감일은 실행한 날(한국 날짜) 기준이라 언제 실행해도 지연·오늘·임박 업무가 보인다.
- 업무는 task_service로 만든다 → 등록·상태 변경 이력과 completed_at이 실제 사용과 같게 남는다.
- 멤버 추가 API(T-F3-01)가 나오기 전이라 멤버십은 ProjectMember를 직접 넣는다.
"""

import sys
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ProjectMember, User
from app.models.enums import ProjectRole, TaskPriority, TaskStatus
from app.schemas.project import ProjectCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import project_service, task_service
from core.clock import get_today
from core.db import SessionLocal
from core.security import hash_password

# 시연 계정 공통 비밀번호 (로컬 시연 전용)
SEED_PASSWORD = "password123"

# (login_id, 이름) — 첫 번째가 프로젝트 OWNER. 프론트 목 데이터와 같은 사람들.
USERS = [
    ("jisoo01", "이지수"),
    ("minho", "김민호"),
    ("seoyeon", "박서연"),
    ("hyunwoo", "최현우"),
]

# (제목, 최종 상태, 우선순위, 담당자, 마감일(오늘+n일, None=없음), 작성자)
_T, _P, _D = TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE
TASKS = [
    ("업무 상태 변경 API", _T, TaskPriority.URGENT, "minho", -3, "jisoo01"),
    ("로그인 화면 오류 문구 정리", _T, TaskPriority.HIGH, "seoyeon", 0, "seoyeon"),
    ("프로젝트 목록 API", _T, TaskPriority.MEDIUM, None, 1, "jisoo01"),
    ("시드 데이터 스크립트 작성", _T, TaskPriority.LOW, "hyunwoo", None, "hyunwoo"),
    ("칸반 보드 API 연결", _P, TaskPriority.HIGH, "minho", 2, "minho"),
    ("업무 등록 모달 검증 문구", _P, TaskPriority.MEDIUM, "jisoo01", 7, "jisoo01"),
    ("멤버 추가 API 권한 테스트", _P, TaskPriority.URGENT, "hyunwoo", -2, "jisoo01"),
    ("회원가입 API", _D, TaskPriority.HIGH, "jisoo01", -4, "jisoo01"),
    ("로그인 API", _D, TaskPriority.HIGH, "minho", -3, "jisoo01"),
    ("DB 스키마 마이그레이션", _D, TaskPriority.URGENT, "hyunwoo", -5, "hyunwoo"),
    ("프로젝트 생성 화면", _D, TaskPriority.MEDIUM, "seoyeon", -1, "seoyeon"),
    ("공통 컴포넌트 정리", _D, TaskPriority.LOW, "seoyeon", None, "minho"),
]


class SeedError(Exception):
    """이미 데이터가 있어 seed를 하지 않을 때."""


def seed(db: Session, today: date) -> None:
    """빈 DB에 시연 데이터를 넣는다. 데이터가 있으면 SeedError."""
    if db.scalar(select(func.count()).select_from(User)):
        raise SeedError("이미 데이터가 있습니다. DB를 비운 뒤 실행해 주세요")

    password_hash = hash_password(SEED_PASSWORD)  # bcrypt는 느려서 한 번만
    users = {
        login_id: User(login_id=login_id, password_hash=password_hash, name=name)
        for login_id, name in USERS
    }
    db.add_all(users.values())
    db.commit()

    owner = users[USERS[0][0]]
    project = project_service.create_project(
        db,
        owner,
        ProjectCreate(
            name="동잇 개발",
            description="11월 팀 프로젝트",
            start_date=today - timedelta(days=8),
            end_date=today + timedelta(days=8),
        ),
    )
    db.add_all(
        ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.MEMBER)
        for user in users.values()
        if user is not owner
    )
    db.commit()

    for title, status, priority, assignee, due, creator in TASKS:
        assignee_user = users[assignee] if assignee else None
        task = task_service.create_task(
            db,
            users[creator],
            project.id,
            TaskCreate(
                title=title,
                priority=priority,
                assignee_id=assignee_user.id if assignee_user else None,
                due_date=None if due is None else today + timedelta(days=due),
            ),
        )
        if status != TaskStatus.TODO:
            # 상태는 담당자가 바꾼 것처럼(없으면 작성자) → 이력의 변경자도 자연스럽게
            actor = assignee_user or users[creator]
            task_service.update_task(db, actor, task.id, TaskUpdate(status=status))


def main() -> None:
    db = SessionLocal()
    try:
        target = db.get_bind().url.database  # 비밀번호 등은 출력하지 않는다
        seed(db, get_today())
    except SeedError as exc:
        print(f"[seed] 멈춤: {exc} (대상 DB: {target})")
        sys.exit(1)
    finally:
        db.close()
    print(
        f"[seed] 완료 (대상 DB: {target}): 사용자 {len(USERS)}명, 프로젝트 1개, "
        f"업무 {len(TASKS)}개. 로그인: {', '.join(u for u, _ in USERS)} "
        f"/ 비밀번호 {SEED_PASSWORD}"
    )


if __name__ == "__main__":
    main()
