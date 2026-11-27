from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from src.lead_intelligence.database.exceptions import (
    PersistenceConflictError,
    PersistenceValidationError,
    RecordNotFoundError,
)


def register_error_handlers(app: FastAPI) -> None:
    # Never return database exception messages, request inputs or tracebacks.
    def handler(status: int, code: str, message: str):
        async def respond(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=status, content={"code": code, "message": message}
            )

        return respond

    app.add_exception_handler(
        RequestValidationError,
        handler(422, "invalid_request", "Invalid request fields."),
    )
    app.add_exception_handler(
        PersistenceValidationError,
        handler(422, "invalid_request", "Invalid request fields."),
    )
    app.add_exception_handler(
        PersistenceConflictError,
        handler(409, "search_conflict", "Search exists or has an active job."),
    )
    app.add_exception_handler(
        RecordNotFoundError,
        handler(404, "not_found", "Requested record not found."),
    )
    app.add_exception_handler(
        OperationalError,
        handler(503, "database_unavailable", "Database temporarily unavailable."),
    )
    app.add_exception_handler(
        SQLAlchemyError,
        handler(500, "database_error", "Database operation failed."),
    )
