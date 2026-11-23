"""프로젝트 삭제와 하위 행 변경이 동시에 일어날 때 교착(1213) → 500이 나지 않는다 (이슈 #72).

프로젝트 삭제는 projects 행을 지우며(배타 잠금) CASCADE로 멤버·업무를 지운다.
멤버 제거·업무 등록·수정·삭제는 먼저 projects 행에 공유 잠금을 걸어 잠그는 순서를
"프로젝트 행 → 하위 행"으로 맞춘다(permissions.lock_project_shared).
→ 둘 중 하나가 먼저 끝나고, 늦은 쪽은 정상 결과 또는 404를 받는다. 500(교착)은 없어야 한다.

교착은 타이밍에 따라 생기므로 같은 경쟁을 여러 번 반복한다.
"""

import threading
from collections.abc import Callable
from functools import partial

from sqlalchemy.orm import Session, sessionmaker

from app.models import ProjectMember, User
from app.models.enums import ProjectRole, TaskStatus
from app.schemas.member import MemberRoleUpdate
from app.schemas.task import TaskCreate, TaskUpdate
from app.services import member_service, project_service, task_service
from core.exceptions import AppError
from tests.factories import add_member, make_project, make_task, make_user

ROUNDS = 8

Action = Callable[[Session, User], None]


def _race(engine, first: tuple[int, Action], second: tuple[int, Action]) -> list[str]:
    """두 요청을 동시에 출발시켜 결과(ok·오류 코드·예상 밖 예외)를 돌려준다."""
    barrier = threading.Barrier(2)
    results: list[str] = ["", ""]

    def run(index: int, actor_id: int, action: Action) -> None:
        session = sessionmaker(bind=engine)()  # 스레드마다 따로 세션
        try:
            actor = session.get(User, actor_id)
            barrier.wait()
            action(session, actor)
            results[index] = "ok"
        except AppError as exc:
            session.rollback()
            results[index] = exc.code
        # 교착(1213) 같은 예상 밖 오류도 기록해야 아래 단언에서 잡힌다
        except Exception as exc:  # noqa: BLE001
            session.rollback()
            results[index] = repr(exc)
        finally:
            session.close()

    threads = [
        threading.Thread(target=run, args=(i, actor_id, action))
        for i, (actor_id, action) in enumerate((first, second))
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)  # 행 잠금 대기 기본값(50초)보다 길게
    assert not any(t.is_alive() for t in threads)
    return results


def _setup(db):
    """OWNER 지수, 업무를 담당하는 MEMBER 민호, 민호 담당 업무 3개."""
    jisu, minho = make_user(db), make_user(db)
    project = make_project(db, jisu)
    add_member(db, project, minho, ProjectRole.MEMBER)
    tasks = [make_task(db, project, jisu, assignee_id=minho.id) for _ in range(3)]
    return jisu, minho, project, tasks


def _delete_project(project_id: int) -> Action:
    return partial(project_service.delete_project, project_id=project_id)


def test_delete_project_vs_remove_member(engine, db):
    for _ in range(ROUNDS):
        jisu, minho, project, _ = _setup(db)
        pid, minho_id = project.id, minho.id

        delete, remove = _race(
            engine,
            (jisu.id, _delete_project(pid)),
            (
                jisu.id,
                partial(
                    member_service.remove_member,
                    project_id=pid,
                    target_user_id=minho_id,
                ),
            ),
        )

        assert delete == "ok"
        assert remove in {"ok", "PROJECT_NOT_FOUND", "MEMBER_NOT_FOUND"}, remove


def test_delete_project_vs_update_task(engine, db):
    for _ in range(ROUNDS):
        jisu, _, project, tasks = _setup(db)
        pid, tid, jisu_id = project.id, tasks[0].id, jisu.id
        # 담당자·상태를 함께 바꿔 멤버 행 공유 잠금과 이력 INSERT까지 일어나게 한다
        body = TaskUpdate(assignee_id=jisu_id, status=TaskStatus.IN_PROGRESS)

        delete, update = _race(
            engine,
            (jisu.id, _delete_project(pid)),
            (jisu.id, partial(task_service.update_task, task_id=tid, data=body)),
        )

        assert delete == "ok"
        assert update in {"ok", "TASK_NOT_FOUND"}, update


def test_delete_project_vs_create_task(engine, db):
    for _ in range(ROUNDS):
        jisu, minho, project, _ = _setup(db)
        pid = project.id
        body = TaskCreate(title="동시 등록", assignee_id=minho.id)

        delete, create = _race(
            engine,
            (jisu.id, _delete_project(pid)),
            (jisu.id, partial(task_service.create_task, project_id=pid, data=body)),
        )

        assert delete == "ok"
        assert create in {"ok", "PROJECT_NOT_FOUND"}, create


def test_delete_project_vs_delete_task(engine, db):
    for _ in range(ROUNDS):
        jisu, _, project, tasks = _setup(db)
        pid, tid = project.id, tasks[0].id

        delete, delete_task = _race(
            engine,
            (jisu.id, _delete_project(pid)),
            (jisu.id, partial(task_service.delete_task, task_id=tid)),
        )

        assert delete == "ok"
        assert delete_task in {"ok", "TASK_NOT_FOUND"}, delete_task


# --- 역할 변경 (PRJ-08, T-F3-06) ---


def _change_role(project_id: int, target_user_id: int, role: ProjectRole) -> Action:
    return partial(
        member_service.change_role,
        project_id=project_id,
        target_user_id=target_user_id,
        data=MemberRoleUpdate(role=role),
    )


def test_delete_project_vs_change_role(engine, db):
    for _ in range(ROUNDS):
        jisu, minho, project, _ = _setup(db)
        pid, minho_id = project.id, minho.id

        delete, change = _race(
            engine,
            (jisu.id, _delete_project(pid)),
            (jisu.id, _change_role(pid, minho_id, ProjectRole.OWNER)),
        )

        assert delete == "ok"
        assert change in {"ok", "PROJECT_NOT_FOUND", "MEMBER_NOT_FOUND"}, change


def test_two_owners_demote_each_other_keeps_one_owner(engine, db):
    """OWNER 2명이 동시에 서로를 MEMBER로 바꿔도 OWNER가 0명이 되지 않는다 (DATABASE-DESIGN §6.1)."""
    for _ in range(ROUNDS):
        jisu, minho = make_user(db), make_user(db)
        project = make_project(db, jisu)
        add_member(db, project, minho, ProjectRole.OWNER)
        pid = project.id

        results = _race(
            engine,
            (jisu.id, _change_role(pid, minho.id, ProjectRole.MEMBER)),
            (minho.id, _change_role(pid, jisu.id, ProjectRole.MEMBER)),
        )

        # 먼저 끝난 쪽은 성공, 늦은 쪽은 이미 자신이 MEMBER라 403 또는 마지막 OWNER라 400
        assert "ok" in results, results
        assert set(results) <= {"ok", "LAST_OWNER", "FORBIDDEN"}, results
        db.rollback()  # 이전 스냅샷이 아니라 두 요청이 커밋한 최신 값을 읽는다
        owners = (
            db.query(ProjectMember)
            .filter_by(project_id=pid, role=ProjectRole.OWNER.value)
            .count()
        )
        assert owners == 1
