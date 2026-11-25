"""테스트 데이터 만들기 함수. 모든 테스트가 같은 방식으로 데이터를 만든다.

근거: ARCHITECTURE §7.
- 각 함수는 마지막에 commit()한다. API 테스트(TestClient)는 다른 세션으로 조회하므로
  커밋된 데이터만 보인다. 테스트끼리는 conftest가 TRUNCATE로 비운다.
- 이력(task_activities)은 만들지 않는다. 이력 기록은 서비스(T-F4-01)의 일이고,
  이력 테스트는 서비스·API를 통해 데이터를 만든다.
"""

import itertools
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, Task, User
from app.models.enums import ProjectRole, TaskStatus
from core.security import create_access_token, hash_password

# 로그인 테스트에서 쓸 공통 비밀번호. 앱과 같은 hash_password()로 한 번만 만든다(bcrypt는 느림).
DEFAULT_PASSWORD = "password123"
DEFAULT_PASSWORD_HASH = hash_password(DEFAULT_PASSWORD)

_seq = itertools.count(1)


def auth_header(user: User) -> dict[str, str]:
    """API 테스트용 인증 헤더. 로그인 API를 거치지 않고 앱과 같은 함수로 토큰을 만든다."""
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def make_user(db: Session, login_id: str | None = None, **fields: Any) -> User:
    """사용자. login_id를 안 주면 user1, user2 … 로 겹치지 않게 만든다."""
    n = next(_seq)
    user = User(
        login_id=login_id or f"user{n}",
        password_hash=fields.pop("password_hash", DEFAULT_PASSWORD_HASH),
        name=fields.pop("name", f"사용자{n}"),
        **fields,
    )
    db.add(user)
    db.commit()
    return user


def make_project(db: Session, owner: User, **fields: Any) -> Project:
    """프로젝트 + 만든 사람을 OWNER 멤버로 추가 (PRJ-01 규칙과 같게)."""
    project = Project(
        name=fields.pop("name", f"프로젝트{next(_seq)}"),
        description=fields.pop("description", "테스트 프로젝트"),  # 필수 (0002)
        created_by=owner.id,
        **fields,
    )
    db.add(project)
    db.flush()  # project.id를 얻는다
    db.add(
        ProjectMember(project_id=project.id, user_id=owner.id, role=ProjectRole.OWNER)
    )
    db.commit()
    return project


def add_member(
    db: Session, project: Project, user: User, role: ProjectRole = ProjectRole.MEMBER
) -> ProjectMember:
    """프로젝트에 멤버 추가. 기본 역할은 MEMBER."""
    member = ProjectMember(project_id=project.id, user_id=user.id, role=role)
    db.add(member)
    db.commit()
    return member


def make_task(db: Session, project: Project, created_by: User, **fields: Any) -> Task:
    """업무. status=DONE을 주고 completed_at을 안 주면 지금(UTC)을 넣는다(ck_tasks_completed_at)."""
    if fields.get("status") == TaskStatus.DONE and "completed_at" not in fields:
        fields["completed_at"] = datetime.now(UTC).replace(tzinfo=None)
    task = Task(
        project_id=project.id,
        created_by=created_by.id,
        title=fields.pop("title", f"업무{next(_seq)}"),
        **fields,
    )
    db.add(task)
    db.commit()
    return task
