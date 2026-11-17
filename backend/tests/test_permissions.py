"""require_project_role 권한 검사 (T-F2-01, API-SPEC §1.5·§10 권한).

API가 아직 없어 서비스 함수를 직접 부른다. API 단위 403 테스트는 T-F2-03·04에서 추가한다.
"""

import pytest

from app.models.enums import ProjectRole
from app.services.permissions import ANY_MEMBER, OWNER_ONLY, require_project_role
from core.exceptions import Forbidden, NotFound
from tests.factories import add_member, make_project, make_user


def test_owner_passes_owner_only(db):
    owner = make_user(db)
    project = make_project(db, owner)

    member = require_project_role(db, project.id, owner, OWNER_ONLY)

    assert member.user_id == owner.id
    assert member.role == ProjectRole.OWNER


def test_member_passes_any_member(db):
    owner, user = make_user(db), make_user(db)
    project = make_project(db, owner)
    add_member(db, project, user)

    member = require_project_role(db, project.id, user, ANY_MEMBER)

    assert member.role == ProjectRole.MEMBER


def test_member_forbidden_for_owner_only(db):
    """MEMBER가 OWNER 전용 작업 → 403 FORBIDDEN"""
    owner, user = make_user(db), make_user(db)
    project = make_project(db, owner)
    add_member(db, project, user)

    with pytest.raises(Forbidden) as exc:
        require_project_role(db, project.id, user, OWNER_ONLY)
    assert exc.value.code == "FORBIDDEN"


def test_non_member_forbidden(db):
    """비멤버 → 403 NOT_PROJECT_MEMBER (역할 검사보다 먼저)"""
    owner, outsider = make_user(db), make_user(db)
    project = make_project(db, owner)

    with pytest.raises(Forbidden) as exc:
        require_project_role(db, project.id, outsider, ANY_MEMBER)
    assert exc.value.code == "NOT_PROJECT_MEMBER"


def test_member_of_other_project_forbidden(db):
    """다른 프로젝트의 OWNER라도 이 프로젝트 멤버가 아니면 403"""
    owner_a, owner_b = make_user(db), make_user(db)
    project_a = make_project(db, owner_a)
    make_project(db, owner_b)

    with pytest.raises(Forbidden) as exc:
        require_project_role(db, project_a.id, owner_b, ANY_MEMBER)
    assert exc.value.code == "NOT_PROJECT_MEMBER"


def test_missing_project_not_found(db):
    """없는 프로젝트 → 404 (멤버 검사보다 먼저)"""
    user = make_user(db)

    with pytest.raises(NotFound) as exc:
        require_project_role(db, 999_999, user, ANY_MEMBER)
    assert exc.value.code == "PROJECT_NOT_FOUND"
