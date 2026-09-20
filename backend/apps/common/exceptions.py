"""
Domain exceptions and the single API error envelope.

Every error the client sees has the same shape, so the React side has one
error path rather than one per endpoint (PRD 9.1):

    { "error": { "code": "...", "message": "...", "details": {...} } }
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError as \
    DjangoValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """
    Base for business-rule violations raised by the service layer.

    Services raise these instead of returning error tuples, so a rule broken
    deep in a call chain cannot be silently ignored by the caller. Views never
    catch them -- the handler below turns them into a 4xx response.
    """

    code = "domain_error"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "The request could not be completed."

    def __init__(self, message=None, code=None, details=None):
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        super().__init__(self.message)


class InvalidStateTransition(DomainError):
    """An illegal move in a state machine -- never a 500 (PRD 8.3)."""

    code = "invalid_state_transition"
    status_code = status.HTTP_409_CONFLICT
    message = "That action is not allowed from the current state."


class RateLimited(DomainError):
    code = "rate_limited"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Too many attempts. Please try again later."


class VerificationError(DomainError):
    code = "verification_failed"
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Verification failed."


class NotFound(DomainError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Not found."


def _envelope(code, message, details=None):
    return {"error": {"code": code, "message": message,
                      "details": details or {}}}


def api_exception_handler(exc, context):
    """
    DRF exception handler producing the single error envelope.

    Registered as DEFAULT_EXCEPTION_HANDLER, so it covers every view.
    """
    if isinstance(exc, DomainError):
        return Response(
            _envelope(exc.code, exc.message, exc.details),
            status=exc.status_code,
        )

    if isinstance(exc, Http404):
        return Response(_envelope("not_found", "Not found."),
                        status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, PermissionDenied):
        return Response(_envelope("permission_denied", "Not permitted."),
                        status=status.HTTP_403_FORBIDDEN)

    if isinstance(exc, DjangoValidationError):
        return Response(
            _envelope("validation_error", "Invalid input.",
                      {"fields": getattr(exc, "message_dict",
                                         {"non_field": exc.messages})}),
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        # Unhandled -- log with traceback and return an opaque 500 so no
        # internal detail leaks to the client.
        logger.exception("Unhandled exception in %s", context.get("view"))
        return Response(
            _envelope("server_error", "An unexpected error occurred."),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    detail = response.data
    if isinstance(detail, dict) and "detail" in detail:
        response.data = _envelope(
            getattr(detail["detail"], "code", "error"),
            str(detail["detail"]),
        )
    else:
        # Serializer field errors arrive as {field: [messages]}.
        response.data = _envelope(
            "validation_error", "Invalid input.", {"fields": detail}
        )
    return response
