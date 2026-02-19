"""Standardized error response utilities for the Forks API."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(message: str, status_code: int) -> JSONResponse:
    """Return a consistent JSON error response.

    All API errors are formatted as::

        {"error": "<message>", "status": <status_code>}

    Args:
        message: Human-readable error description.
        status_code: HTTP status code for the response.

    Returns:
        A :class:`JSONResponse` with the standardized error body.
    """
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "status": status_code},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Global handler for HTTP exceptions.

    Normalizes all :class:`HTTPException` responses to the standard
    ``{"error": ..., "status": ...}`` format instead of FastAPI's default
    ``{"detail": ...}`` format.
    """
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return error_response(message, exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Global handler for request validation errors (422).

    Converts Pydantic validation errors from FastAPI's default list format
    into the standard ``{"error": ..., "status": 422}`` format.
    """
    errors = exc.errors()
    if errors:
        first = errors[0]
        field = ".".join(str(loc) for loc in first.get("loc", []) if loc != "body")
        msg = first.get("msg", "Validation error")
        message = f"{field}: {msg}" if field else msg
    else:
        message = "Invalid request"
    return error_response(message, 422)
