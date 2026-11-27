"""Cookie authentication for the same-origin HTTP API."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.lead_intelligence.auth.security import normalize_username
from src.lead_intelligence.auth.service import (
    AuthenticationService,
    InvalidCredentialsError,
    InvalidSessionError,
    PasswordChangeRequiredError,
    Principal,
)


@dataclass(frozen=True, slots=True)
class AuthConfig:
    origin: str = "https://localhost"
    development_http: bool = False

    def __post_init__(self) -> None:
        parsed = urlsplit(self.origin)
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or self.origin != f"{parsed.scheme}://{parsed.netloc}"
        ):
            raise ValueError("Configure an exact application origin without a path")
        if self.development_http:
            if parsed.scheme != "http" or parsed.hostname not in {
                "127.0.0.1",
                "localhost",
                "::1",
            }:
                raise ValueError("Development HTTP requires a loopback origin")
        elif parsed.scheme != "https":
            raise ValueError("Authentication requires HTTPS")

    @classmethod
    def load(cls) -> "AuthConfig":
        development = os.getenv("BLI_AUTH_DEV_HTTP", "0") == "1"
        default = "http://127.0.0.1:8000" if development else "https://localhost"
        return cls(os.getenv("BLI_AUTH_ORIGIN", default), development)

    @property
    def cookie_name(self) -> str:
        return "bli_dev_session" if self.development_http else "__Host-bli_session"


class LoginLimiter:
    """Bounded, per-process sliding window and hash concurrency guard."""

    def __init__(self) -> None:
        self.lock = Lock()
        self.slots = BoundedSemaphore(2)
        self.attempts: list[tuple[float, str, str]] = []

    @contextmanager
    def attempt(self, peer: str, account: str) -> Iterator[None]:
        with self.lock:
            now = monotonic()
            self.attempts = [entry for entry in self.attempts if now - entry[0] < 60]
            if (
                len(self.attempts) >= 30
                or sum(entry[1] == peer for entry in self.attempts) >= 10
                or sum(entry[2] == account for entry in self.attempts) >= 5
                or not self.slots.acquire(blocking=False)
            ):
                raise HTTPException(
                    429,
                    "Too many authentication attempts",
                    headers={"Retry-After": "60"},
                )
            self.attempts.append((now, peer, account))
        try:
            yield
        finally:
            self.slots.release()


def _config(request: Request) -> AuthConfig:
    config = request.app.state.auth_config
    if f"{request.url.scheme}://{request.url.netloc}" != config.origin:
        raise HTTPException(403, "Invalid application origin")
    if config.development_http and (
        request.client is None or request.client.host not in {"127.0.0.1", "::1"}
    ):
        raise HTTPException(403, "Development authentication is loopback only")
    return config


def require_csrf(
    request: Request,
    csrf: Annotated[str | None, Header(alias="X-BLI-CSRF")] = None,
) -> None:
    config = _config(request)
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    if (
        csrf != "1"
        or (origin is not None and origin != config.origin)
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(403, "CSRF validation failed")


def _token(request: Request) -> str:
    config = _config(request)
    token = request.cookies.get(config.cookie_name)
    if not token:
        raise HTTPException(401, "Authentication required")
    return token


def _authenticate(request: Request, *, allow_password_change: bool) -> Principal:
    token = _token(request)
    # Separate short transaction: never hold the user lock during exports.
    with request.app.state.session_factory.begin() as session:
        return AuthenticationService(session).authenticate(
            token, allow_password_change=allow_password_change
        )


def require_user(
    request: Request, _: Annotated[None, Depends(require_csrf)]
) -> Principal:
    return _authenticate(request, allow_password_change=False)


def require_admin(principal: Annotated[Principal, Depends(require_user)]) -> Principal:
    if principal.role != "admin":
        raise HTTPException(403, "Administrator access required")
    return principal


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024, repr=False)


class PasswordInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    current_password: str = Field(min_length=1, max_length=1024, repr=False)
    new_password: str = Field(min_length=15, max_length=1024, repr=False)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    display_name: str
    role: str
    must_change_password: bool


def _public(principal: Principal) -> UserResponse:
    return UserResponse(
        id=principal.id,
        username=principal.username,
        display_name=principal.display_name,
        role=principal.role,
        must_change_password=principal.must_change_password,
    )


def _clear_cookie(request: Request, response: Response) -> None:
    config = _config(request)
    response.delete_cookie(
        config.cookie_name,
        path="/",
        secure=not config.development_http,
        httponly=True,
        samesite="strict",
    )


def _peer(request: Request) -> str:
    return request.client.host if request.client else "unknown"


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
CsrfDep = Annotated[None, Depends(require_csrf)]


@router.post("/login")
def login(
    body: LoginInput, request: Request, response: Response, _: CsrfDep
) -> UserResponse:
    config = _config(request)
    try:
        account = normalize_username(body.username)
    except ValueError:
        account = "invalid"
    with request.app.state.login_limiter.attempt(_peer(request), account):
        with request.app.state.session_factory.begin() as session:
            result = AuthenticationService(session).login(body.username, body.password)
    response.set_cookie(
        config.cookie_name,
        result.token,
        expires=result.expires_at,
        path="/",
        secure=not config.development_http,
        httponly=True,
        samesite="strict",
    )
    return _public(result.principal)


@router.get("/me")
def me(request: Request) -> UserResponse:
    return _public(_authenticate(request, allow_password_change=True))


@router.post("/logout", status_code=204, response_class=Response)
def logout(request: Request, _: CsrfDep) -> Response:
    config = _config(request)
    token = request.cookies.get(config.cookie_name)
    if token:
        with request.app.state.session_factory.begin() as session:
            AuthenticationService(session).logout(token)
    response = Response(status_code=204)
    _clear_cookie(request, response)
    return response


@router.post("/change-password", status_code=204, response_class=Response)
def change_password(body: PasswordInput, request: Request, _: CsrfDep) -> Response:
    token = _token(request)
    with request.app.state.login_limiter.attempt(_peer(request), "password-change"):
        with request.app.state.session_factory.begin() as session:
            try:
                AuthenticationService(session).change_password(
                    token, body.current_password, body.new_password
                )
            except ValueError:
                raise HTTPException(422, "Invalid replacement password") from None
    response = Response(status_code=204)
    _clear_cookie(request, response)
    return response


def register_auth_errors(app: FastAPI) -> None:
    async def unauthorized(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"code": "invalid_credentials", "message": "Authentication failed"},
        )

    async def password_required(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "code": "password_change_required",
                "message": "Change your password before continuing",
            },
        )

    app.add_exception_handler(InvalidCredentialsError, unauthorized)
    app.add_exception_handler(InvalidSessionError, unauthorized)
    app.add_exception_handler(PasswordChangeRequiredError, password_required)
