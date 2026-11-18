"""시연 데이터 seed 테스트 (T-F0-10, DATABASE-DESIGN 시드, UI-DESIGN S4).

테스트 DB(db 픽스처)에 seed()를 실행해 결과를 확인한다. 개발 DB는 건드리지 않는다.
완료 기준: 빈 DB에 실행 후 시연 가능 / 이미 데이터가 있으면 아무것도 넣지 않고 멈춤.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, Task, TaskActivity, User
from app.models.enums import TaskStatus
from scripts.seed import SEED_PASSWORD, SeedError, seed
from tests.factories import make_user

TODAY = date(2026, 11, 18)


def _count(db: Session, model, *where) -> int:
    return db.scalar(select(func.count()).select_from(model).where(*where))


def test_seed_creates_demo_data(db: Session) -> None:
    seed(db, TODAY)

    assert _count(db, User) == 4
    assert _count(db, Project) == 1
    assert _count(db, ProjectMember) == 4
    assert _count(db, ProjectMember, ProjectMember.role == "OWNER") == 1
    assert _count(db, Task) == 12
    # UI-DESIGN S4 예시: 할 일 4 · 진행 중 3 · 완료 5
    assert _count(db, Task, Task.status == TaskStatus.TODO) == 4
    assert _count(db, Task, Task.status == TaskStatus.IN_PROGRESS) == 3
    assert _count(db, Task, Task.status == TaskStatus.DONE) == 5
    assert (
        _count(db, Task, Task.status == TaskStatus.DONE, Task.completed_at.is_(None))
        == 0
    )


def test_seed_has_overdue_and_due_soon(db: Session) -> None:
    """대시보드 시연용: 미완료 업무 중 지연(오늘 전)과 임박(오늘~3일 뒤)이 모두 있다."""
    seed(db, TODAY)

    not_done = Task.status != TaskStatus.DONE
    assert _count(db, Task, not_done, Task.due_date < TODAY) >= 1
    assert (
        _count(
            db,
            Task,
            not_done,
            Task.due_date >= TODAY,
            Task.due_date <= TODAY + timedelta(days=3),
        )
        >= 1
    )
    # 임박의 끝(오늘+3일, DASH-03 "3일 이내" 경계)을 보여 줄 업무가 있다
    assert _count(db, Task, not_done, Task.due_date == TODAY + timedelta(days=3)) >= 1
    assert _count(db, Task, Task.due_date.is_(None)) >= 1


def test_seed_records_activities(db: Session) -> None:
    """업무를 서비스로 만들어 이력이 실제 사용과 같게 남는다."""
    seed(db, TODAY)

    assert _count(db, TaskActivity, TaskActivity.action == "CREATED") == 12
    # 진행 중 3 + 완료 5 = 상태 변경 정확히 8번 (중복 기록이 생기면 잡힌다)
    assert (
        _count(
            db,
            TaskActivity,
            TaskActivity.action == "UPDATED",
            TaskActivity.field == "status",
        )
        == 8
    )
    # 상태 외에는 바꾸지 않으므로 다른 UPDATED 이력은 없다
    assert _count(db, TaskActivity, TaskActivity.action == "UPDATED") == 8


def test_seed_user_can_login(db: Session, client) -> None:
    seed(db, TODAY)

    res = client.post(
        "/api/auth/login", json={"login_id": "minho", "password": SEED_PASSWORD}
    )

    assert res.status_code == 200


def test_seed_refuses_when_data_exists(db: Session) -> None:
    make_user(db)

    with pytest.raises(SeedError):
        seed(db, TODAY)

    db.rollback()
    assert _count(db, User) == 1  # 아무것도 더 넣지 않았다
    assert _count(db, Task) == 0
