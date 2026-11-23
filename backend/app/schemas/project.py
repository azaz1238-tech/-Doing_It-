"""프로젝트 요청·응답 스키마 (API-SPEC §4 Project, §5.2, REQUIREMENTS PRJ-01·03)."""

from datetime import date
from typing import Annotated

from fastapi.exceptions import RequestValidationError
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.models import Project
from app.models.enums import ProjectRole
from app.schemas.common import UtcDatetime

NAME_MAX = 30
NAME_MESSAGE = "프로젝트 이름은 1~30자로 입력해 주세요"  # SPEC PRJ-01-b
PERIOD_MESSAGE = "종료일은 시작일 이후여야 합니다"  # SPEC PRJ-01-c
DESCRIPTION_MAX = 2000
# 설명 필수 (11/22 팀장 결정 — 명세 반영 예정)
DESCRIPTION_MESSAGE = "프로젝트 설명을 입력해 주세요"


def _check_description_not_blank(value: str) -> str:
    if not value:
        raise ValueError(DESCRIPTION_MESSAGE)
    return value


def _description_not_null(value: object) -> object:
    """빠뜨렸거나 null을 보낸 경우도 '필수 항목입니다' 대신 설명 전용 문구를 쓴다."""
    if value is None:
        raise ValueError(DESCRIPTION_MESSAGE)
    return value


# 앞뒤 공백 제거 후 1~2000자 (API-SPEC v1.3 §5.2, SPEC-CHANGELOG #15).
# 최대가 없으면 DB TEXT 한도 초과로 500.
ProjectDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=DESCRIPTION_MAX),
    AfterValidator(_check_description_not_blank),
]


def _check_name_length(value: str) -> str:
    if not 1 <= len(value) <= NAME_MAX:
        raise ValueError(NAME_MESSAGE)
    return value


# 앞뒤 공백 제거 후 1~30자. 한글도 1자로 센다.
ProjectName = Annotated[
    str, StringConstraints(strip_whitespace=True), AfterValidator(_check_name_length)
]


def is_period_valid(start: date | None, end: date | None) -> bool:
    """둘 중 하나라도 없으면 통과. 둘 다 있으면 종료일 >= 시작일 (DB ck_projects_period와 같은 규칙)."""
    return not (start and end and end < start)


def period_error() -> RequestValidationError:
    """저장될 최종 값으로 기간을 검사하다 실패했을 때 쓰는 422.

    본문만 보고는 알 수 없어(end_date만 보낸 경우) 서비스에서 던진다.
    공통 처리기가 다른 422와 같은 { code, message, errors[] } 형식으로 바꾼다.
    """
    return RequestValidationError(
        [{"type": "value_error", "loc": ("body", "end_date"), "msg": PERIOD_MESSAGE}]
    )


class _PeriodCheck(BaseModel):
    """본문에 두 날짜가 다 있으면 스키마에서 먼저 막는다 (422가 404·403보다 먼저)."""

    @field_validator("end_date", check_fields=False)
    @classmethod
    def _check_period(cls, end: date | None, info: ValidationInfo) -> date | None:
        # 오류를 end_date 칸에 붙이려고 모델 검증이 아니라 필드 검증으로 한다
        if not is_period_valid(info.data.get("start_date"), end):
            raise ValueError(PERIOD_MESSAGE)
        return end


class ProjectCreate(_PeriodCheck):
    model_config = ConfigDict(extra="forbid")

    name: ProjectName
    # 필수. 빠뜨려도 검증하도록 기본값 None을 검사한다 (_description_not_null에서 422)
    description: ProjectDescription = Field(default=None, validate_default=True)
    start_date: date | None = None
    end_date: date | None = None

    _check_description_null = field_validator("description", mode="before")(
        _description_not_null
    )


class ProjectUpdate(_PeriodCheck):
    """바꿀 필드만 보낸다. 날짜는 null로 비울 수 있고, name·description은 비울 수 없다."""

    model_config = ConfigDict(extra="forbid")

    name: ProjectName | None = None
    description: ProjectDescription | None = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _name_not_null(cls, value: object) -> object:
        # 명시적으로 null을 보낸 경우만 여기 걸린다 (안 보내면 검증하지 않음)
        if value is None:
            raise ValueError(NAME_MESSAGE)
        return value

    # 명시적으로 null을 보낸 경우만 걸린다 (안 보내면 기존 설명 유지)
    _check_description_null = field_validator("description", mode="before")(
        _description_not_null
    )


class ProgressOut(BaseModel):
    """프로젝트 진행률 (DASH-01, API-SPEC §4). 업무가 없으면 0%."""

    total: int = 0
    done: int = 0
    percent: int = 0

    @classmethod
    def of(cls, total: int, done: int) -> "ProgressOut":
        # 반올림(0.5 올림) = DATABASE-DESIGN §8.3 ROUND. 정수 계산이라 오차 없음
        percent = (200 * done + total) // (2 * total) if total else 0
        return cls(total=total, done=done, percent=percent)


class ProjectOut(BaseModel):
    """Project 객체 (API-SPEC §4). my_role은 요청한 사용자의 역할."""

    id: int
    name: str
    description: str
    start_date: date | None
    end_date: date | None
    my_role: ProjectRole
    progress: ProgressOut
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @classmethod
    def of(
        cls, project: Project, role: str, progress: ProgressOut | None = None
    ) -> "ProjectOut":
        return cls(
            id=project.id,
            name=project.name,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            my_role=role,
            progress=progress or ProgressOut(),  # 새 프로젝트는 업무 0개
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
