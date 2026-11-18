"""멤버 목록 API (T-F3-02, PRJ-07, API-SPEC §5.3).

완료 기준: 이름·아이디·역할 / OWNER 먼저 → joined_at → id / 비멤버 403.
"""

from datetime import datetime

from app.models import ProjectMember
from app.models.enums import ProjectRole
from core.security import create_access_token
from tests.factories import add_member, make_project, make_user


def _url(project_id: int) -> str:
    return f"/api/projects/{project_id}/members"


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _join(db, project, user, role, joined_at) -> None:
    """joined_at을 정해서 멤버 추가 (정렬 테스트용)."""
    db.add(
        ProjectMember(
            project_id=project.id, user_id=user.id, role=role, joined_at=joined_at
        )
    )
    db.commit()


# --- 성공 ---


def test_list_200_member_fields(client, db):
    owner = make_user(db, login_id="jisu", name="지수")
    minho = make_user(db, login_id="minho", name="민호")
    project = make_project(db, owner)
    add_member(db, project, minho)

    # MEMBER도 볼 수 있다 (담당자 선택지)
    res = client.get(_url(project.id), headers=_auth(minho))

    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["size"] == 20
    assert set(body["items"][1]) == {"user_id", "login_id", "name", "role", "joined_at"}
    assert (
        body["items"][1]["user_id"] == minho.id
    )  # project_members.id가 아니라 users.id
    assert body["items"][1]["login_id"] == "minho"
    assert body["items"][1]["name"] == "민호"
    assert body["items"][1]["role"] == "MEMBER"
    assert body["items"][1]["joined_at"].endswith("Z")
    assert "password_hash" not in res.text


def test_list_order_owner_first_then_joined_at_then_id(client, db):
    owner = make_user(db, login_id="owner")
    project = make_project(db, owner)
    early, late, same1, same2, owner2 = (make_user(db) for _ in range(5))
    t = datetime(2026, 11, 18, 1, 0, 0)
    # 기존 OWNER 행의 joined_at을 가장 늦게 바꿔도 OWNER가 먼저 나와야 한다
    db.query(ProjectMember).filter_by(user_id=owner.id).update(
        {"joined_at": datetime(2026, 11, 18, 9, 0, 0)}
    )
    db.commit()
    _join(db, project, late, ProjectRole.MEMBER, t.replace(hour=5))
    _join(db, project, early, ProjectRole.MEMBER, t.replace(hour=2))
    _join(db, project, same1, ProjectRole.MEMBER, t.replace(hour=3))
    _join(db, project, same2, ProjectRole.MEMBER, t.replace(hour=3))  # 같은 초 → id 순
    _join(db, project, owner2, ProjectRole.OWNER, t.replace(hour=4))

    res = client.get(_url(project.id), headers=_auth(owner))

    ids = [m["user_id"] for m in res.json()["items"]]
    assert ids == [owner2.id, owner.id, early.id, same1.id, same2.id, late.id]


def test_list_pagination(client, db):
    owner = make_user(db)
    project = make_project(db, owner)
    for _ in range(4):
        add_member(db, project, make_user(db))

    res = client.get(
        _url(project.id), params={"page": 2, "size": 2}, headers=_auth(owner)
    )

    body = res.json()
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
    assert len(body["items"]) == 2


def test_list_size_100_allowed_101_422(client, db):
    owner = make_user(db)
    project = make_project(db, owner)

    ok = client.get(_url(project.id), params={"size": 100}, headers=_auth(owner))
    bad = client.get(_url(project.id), params={"size": 101}, headers=_auth(owner))

    assert ok.status_code == 200
    assert bad.status_code == 422


# --- 실패 ---


def test_list_non_member_403(client, db):  # PRJ-07-a
    owner, outsider = make_user(db), make_user(db)
    project = make_project(db, owner)

    res = client.get(_url(project.id), headers=_auth(outsider))

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"
    assert owner.login_id not in res.text  # 멤버 정보가 새지 않는다


def test_list_not_found_404(client, db):
    res = client.get(_url(999999), headers=_auth(make_user(db)))

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


def test_list_without_token_401(client, db):
    owner = make_user(db)
    project = make_project(db, owner)

    res = client.get(_url(project.id))

    assert res.status_code == 401
