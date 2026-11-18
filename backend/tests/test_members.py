"""멤버 목록·추가 API (T-F3-02·01, PRJ-07·04, API-SPEC §5.3).

완료 기준: 목록 — 이름·아이디·역할 / OWNER 먼저 → joined_at → id / 비멤버 403.
          추가 — 없는 아이디 404, 중복 409, MEMBER 403.
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
    # 정렬과 상관없이 필드만 본다 (user_id는 project_members.id가 아니라 users.id)
    item = next(m for m in body["items"] if m["user_id"] == minho.id)
    assert set(item) == {"user_id", "login_id", "name", "role", "joined_at"}
    assert item["login_id"] == "minho"
    assert item["name"] == "민호"
    assert item["role"] == "MEMBER"
    assert item["joined_at"].endswith("Z")
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


# --- 추가 (PRJ-04) ---


def _add(client, project_id, caller, **body):
    payload = {"login_id": "minho", "role": "MEMBER", **body}
    headers = _auth(caller) if caller else {}
    return client.post(_url(project_id), headers=headers, json=payload)


def test_add_201(client, db):  # PRJ-04-a
    owner = make_user(db)
    minho = make_user(db, login_id="minho", name="민호")
    project = make_project(db, owner)

    res = _add(client, project.id, owner)

    assert res.status_code == 201
    body = res.json()
    assert set(body) == {"user_id", "login_id", "name", "role", "joined_at"}
    assert body["user_id"] == minho.id
    assert body["name"] == "민호"
    assert body["role"] == "MEMBER"
    assert body["joined_at"].endswith("Z")
    # 민호의 프로젝트 목록에 P가 바로 나타난다
    mine = client.get("/api/projects", headers=_auth(minho)).json()
    assert [p["id"] for p in mine["items"]] == [project.id]


def test_add_trims_and_lowercases_login_id_201(client, db):
    owner = make_user(db)
    make_user(db, login_id="minho")
    project = make_project(db, owner)

    res = _add(client, project.id, owner, login_id=" MinHo ")

    assert res.status_code == 201
    assert res.json()["login_id"] == "minho"


def test_add_as_owner_201(client, db):
    owner = make_user(db)
    make_user(db, login_id="minho")
    project = make_project(db, owner)

    res = _add(client, project.id, owner, role="OWNER")

    assert res.status_code == 201
    assert res.json()["role"] == "OWNER"


def test_add_unknown_login_id_404(client, db):  # PRJ-04-b
    owner = make_user(db)
    project = make_project(db, owner)

    res = _add(client, project.id, owner, login_id="nobody")

    assert res.status_code == 404
    assert res.json() == {
        "code": "USER_NOT_FOUND",
        "message": "해당 아이디의 회원이 없습니다",
    }


def test_add_inactive_user_404(client, db):  # API-SPEC §5.3 (v1.2)
    owner = make_user(db)
    make_user(db, login_id="minho", is_active=False)
    project = make_project(db, owner)

    res = _add(client, project.id, owner)

    assert res.status_code == 404
    assert res.json()["code"] == "USER_NOT_FOUND"  # 계정 상태를 드러내지 않는다
    db.rollback()
    assert db.query(ProjectMember).filter_by(project_id=project.id).count() == 1


def test_add_duplicate_409(client, db):  # PRJ-04-c
    owner = make_user(db)
    minho = make_user(db, login_id="minho")
    project = make_project(db, owner)
    add_member(db, project, minho)

    res = _add(client, project.id, owner)

    assert res.status_code == 409
    assert res.json() == {
        "code": "ALREADY_MEMBER",
        "message": "이미 프로젝트 멤버입니다",
    }
    db.rollback()
    assert db.query(ProjectMember).filter_by(project_id=project.id).count() == 2


def test_add_by_member_403(client, db):  # PRJ-04-d
    owner, member = make_user(db), make_user(db)
    make_user(db, login_id="minho")
    project = make_project(db, owner)
    add_member(db, project, member)

    res = _add(client, project.id, member)

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_add_by_member_unknown_login_id_403(client, db):  # API-SPEC §5.3 (v1.2)
    """없는 아이디여도 MEMBER에게는 404가 아니라 403 — 아이디 존재 여부를 숨긴다."""
    owner, member = make_user(db), make_user(db)
    project = make_project(db, owner)
    add_member(db, project, member)

    res = _add(client, project.id, member, login_id="nobody")

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"


def test_add_by_non_member_403(client, db):
    owner, outsider = make_user(db), make_user(db)
    make_user(db, login_id="minho")
    project = make_project(db, owner)

    res = _add(client, project.id, outsider)

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_add_project_not_found_404(client, db):
    res = _add(client, 999999, make_user(db))

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


def test_add_invalid_body_422(client, db):
    owner = make_user(db)
    project = make_project(db, owner)

    bad_role = _add(client, project.id, owner, role="VIEWER")
    missing = client.post(
        _url(project.id), headers=_auth(owner), json={"login_id": "minho"}
    )
    extra = _add(client, project.id, owner, is_admin=True)

    assert bad_role.status_code == 422
    assert missing.status_code == 422
    assert extra.status_code == 422


def test_add_without_token_401(client, db):
    project = make_project(db, make_user(db))

    res = _add(client, project.id, None)

    assert res.status_code == 401


def test_add_without_token_invalid_body_401(
    client, db
):  # API-SPEC §8: 422가 아니라 401
    project = make_project(db, make_user(db))

    res = _add(client, project.id, None, role="VIEWER")

    assert res.status_code == 401
