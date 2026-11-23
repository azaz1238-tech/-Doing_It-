"""멤버 역할 변경 API (T-F3-06, PRJ-08, API-SPEC §6).

완료 기준: 마지막 OWNER를 MEMBER로 내리면 400 LAST_OWNER (PRJ-08-a).
          MEMBER·비멤버 403, 대상이 멤버가 아니면 404, 잘못된 역할 값 422.
"""

from app.models import ProjectMember
from app.models.enums import ProjectRole
from core.security import create_access_token
from tests.factories import add_member, make_project, make_user


def _url(project_id: int, user_id: int) -> str:
    return f"/api/projects/{project_id}/members/{user_id}"


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


def _role_in_db(db, project, user) -> str:
    # API는 다른 세션에서 커밋한다. 트랜잭션을 끝내야 이전 스냅샷이 아니라 최신 값을 읽는다.
    db.rollback()
    return (
        db.query(ProjectMember)
        .filter_by(project_id=project.id, user_id=user.id)
        .one()
        .role
    )


def _setup(db):
    """OWNER 지수 1명, MEMBER 민호."""
    jisu = make_user(db, login_id="jisu", name="지수")
    minho = make_user(db, login_id="minho", name="민호")
    project = make_project(db, jisu)
    add_member(db, project, minho, ProjectRole.MEMBER)
    return jisu, minho, project


# --- 성공 ---


def test_promote_member_to_owner_200(client, db):
    jisu, minho, project = _setup(db)

    res = client.patch(
        _url(project.id, minho.id), json={"role": "OWNER"}, headers=_auth(jisu)
    )

    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"user_id", "login_id", "name", "role", "joined_at"}
    assert body["user_id"] == minho.id
    assert body["login_id"] == "minho"
    assert body["name"] == "민호"
    assert body["role"] == "OWNER"
    assert body["joined_at"].endswith("Z")
    assert "password_hash" not in res.text
    assert _role_in_db(db, project, minho) == "OWNER"


def test_prj_08_a_demote_self_after_promoting_other_200(client, db):
    """PRJ-08-a 뒷부분: 민호를 OWNER로 바꾼 뒤에는 지수가 자신을 MEMBER로 바꿀 수 있다."""
    jisu, minho, project = _setup(db)
    client.patch(
        _url(project.id, minho.id), json={"role": "OWNER"}, headers=_auth(jisu)
    )

    res = client.patch(
        _url(project.id, jisu.id), json={"role": "MEMBER"}, headers=_auth(jisu)
    )

    assert res.status_code == 200
    assert res.json()["role"] == "MEMBER"
    assert _role_in_db(db, project, jisu) == "MEMBER"
    assert _role_in_db(db, project, minho) == "OWNER"


def test_same_role_200_no_change(client, db):
    jisu, minho, project = _setup(db)

    res = client.patch(
        _url(project.id, minho.id), json={"role": "MEMBER"}, headers=_auth(jisu)
    )

    assert res.status_code == 200
    assert res.json()["role"] == "MEMBER"
    assert _role_in_db(db, project, minho) == "MEMBER"


def test_sole_owner_set_owner_again_200(client, db):
    """마지막 OWNER라도 OWNER → OWNER는 OWNER 수가 줄지 않으므로 허용."""
    jisu, _, project = _setup(db)

    res = client.patch(
        _url(project.id, jisu.id), json={"role": "OWNER"}, headers=_auth(jisu)
    )

    assert res.status_code == 200
    assert res.json()["role"] == "OWNER"


# --- 실패 ---


def test_prj_08_a_demote_last_owner_400(client, db):
    """PRJ-08-a: OWNER가 지수 1명뿐일 때 자신을 MEMBER로 바꾸면 거절된다."""
    jisu, _, project = _setup(db)

    res = client.patch(
        _url(project.id, jisu.id), json={"role": "MEMBER"}, headers=_auth(jisu)
    )

    assert res.status_code == 400
    assert res.json()["code"] == "LAST_OWNER"
    assert res.json()["message"] == "OWNER는 최소 1명 있어야 합니다"
    assert _role_in_db(db, project, jisu) == "OWNER"


def test_member_caller_403_forbidden(client, db):
    _, minho, project = _setup(db)

    # MEMBER가 자기 자신을 OWNER로 올리려는 시도
    res = client.patch(
        _url(project.id, minho.id), json={"role": "OWNER"}, headers=_auth(minho)
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
    assert _role_in_db(db, project, minho) == "MEMBER"


def test_member_caller_cannot_demote_owner_403(client, db):
    jisu, minho, project = _setup(db)

    res = client.patch(
        _url(project.id, jisu.id), json={"role": "MEMBER"}, headers=_auth(minho)
    )

    assert res.status_code == 403
    assert res.json()["code"] == "FORBIDDEN"
    assert _role_in_db(db, project, jisu) == "OWNER"


def test_non_member_caller_403(client, db):
    _, minho, project = _setup(db)
    outsider = make_user(db)

    res = client.patch(
        _url(project.id, minho.id), json={"role": "OWNER"}, headers=_auth(outsider)
    )

    assert res.status_code == 403
    assert res.json()["code"] == "NOT_PROJECT_MEMBER"


def test_target_not_member_404(client, db):
    jisu, _, project = _setup(db)
    outsider = make_user(db)

    res = client.patch(
        _url(project.id, outsider.id), json={"role": "OWNER"}, headers=_auth(jisu)
    )

    assert res.status_code == 404
    assert res.json()["code"] == "MEMBER_NOT_FOUND"


def test_target_user_not_exist_404(client, db):
    jisu, _, project = _setup(db)

    res = client.patch(
        _url(project.id, 999_999), json={"role": "OWNER"}, headers=_auth(jisu)
    )

    assert res.status_code == 404
    assert res.json()["code"] == "MEMBER_NOT_FOUND"


def test_project_not_found_404(client, db):
    jisu, minho, _ = _setup(db)

    res = client.patch(
        _url(999_999, minho.id), json={"role": "OWNER"}, headers=_auth(jisu)
    )

    assert res.status_code == 404
    assert res.json()["code"] == "PROJECT_NOT_FOUND"


def test_invalid_role_422(client, db):
    jisu, minho, project = _setup(db)

    for body in ({"role": "VIEWER"}, {"role": None}, {}, {"role": "OWNER", "x": 1}):
        res = client.patch(_url(project.id, minho.id), json=body, headers=_auth(jisu))
        assert res.status_code == 422, body
        assert res.json()["errors"], body


def test_no_token_401(client, db):
    _, minho, project = _setup(db)

    res = client.patch(_url(project.id, minho.id), json={"role": "OWNER"})

    assert res.status_code == 401
