"""Administrator-only employee management. No role changes or deletion."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from src.lead_intelligence.api.auth import CsrfDep, _peer, _token, require_admin
from src.lead_intelligence.auth.admin import (
    EmployeeExistsError,
    EmployeeNotFoundError,
    EmployeeService,
)
from src.lead_intelligence.auth.service import AuthenticationService


class EmployeeInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=15, max_length=1024, repr=False)


class EmployeeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set or any(
            getattr(self, name) is None for name in self.model_fields_set
        ):
            raise ValueError("Provide non-null employee changes")
        return self


class PasswordResetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    password: str = Field(min_length=15, max_length=1024, repr=False)


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    display_name: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None


class EmployeePage(BaseModel):
    items: list[EmployeeResponse]
    limit: int
    offset: int
    has_more: bool


router = APIRouter(prefix="/api/v1/admin/users", tags=["Administration"])


def _authorized_service(request: Request, session: Session) -> EmployeeService:
    # Keep the admin row locked through the operation. Password changes and
    # logout cannot race past the authorization check before commit.
    principal = AuthenticationService(session).authenticate(_token(request))
    require_admin(principal)
    return EmployeeService(session)


@router.post("", status_code=201)
def create_employee(
    body: EmployeeInput, request: Request, _: CsrfDep
) -> EmployeeResponse:
    with request.app.state.session_factory.begin() as session:
        service = _authorized_service(request, session)
        with request.app.state.login_limiter.attempt(_peer(request), "admin-create"):
            try:
                user = service.create(body.username, body.display_name, body.password)
            except EmployeeExistsError:
                raise HTTPException(409, "Username already exists") from None
            except ValueError:
                raise HTTPException(422, "Invalid employee credentials") from None
        result = EmployeeResponse.model_validate(user)
    return result


@router.get("")
def list_employees(
    request: Request,
    _: CsrfDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=2147483647)] = 0,
) -> EmployeePage:
    with request.app.state.session_factory.begin() as session:
        service = _authorized_service(request, session)
        users = service.list(limit=limit + 1, offset=offset)
        return EmployeePage(
            items=[EmployeeResponse.model_validate(user) for user in users[:limit]],
            limit=limit,
            offset=offset,
            has_more=len(users) > limit,
        )


@router.patch("/{user_id}")
def update_employee(
    user_id: UUID, body: EmployeeUpdate, request: Request, _: CsrfDep
) -> EmployeeResponse:
    with request.app.state.session_factory.begin() as session:
        service = _authorized_service(request, session)
        try:
            user = service.update(
                user_id, display_name=body.display_name, is_active=body.is_active
            )
        except EmployeeNotFoundError:
            raise HTTPException(404, "Employee not found") from None
        except ValueError:
            raise HTTPException(422, "Invalid display name") from None
        result = EmployeeResponse.model_validate(user)
    return result


@router.post("/{user_id}/reset-password", status_code=204, response_class=Response)
def reset_employee_password(
    user_id: UUID, body: PasswordResetInput, request: Request, _: CsrfDep
) -> Response:
    with request.app.state.session_factory.begin() as session:
        service = _authorized_service(request, session)
        with request.app.state.login_limiter.attempt(_peer(request), "admin-reset"):
            try:
                service.reset_password(user_id, body.password)
            except EmployeeNotFoundError:
                raise HTTPException(404, "Employee not found") from None
            except ValueError:
                raise HTTPException(422, "Invalid replacement password") from None
    return Response(status_code=204)
