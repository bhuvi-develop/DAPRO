"""Domain errors mapped to the LLD error envelope."""
from typing import Any


class BusinessError(Exception):
    status_code = 409

    def __init__(self, code: str, message: str, next_step: str | None = None, status: int | None = None,
                 details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.next_step = next_step
        self.details = details or []
        if status:
            self.status_code = status


class NotFound(BusinessError):
    def __init__(self, what: str = "Record") -> None:
        super().__init__("NOT_FOUND", f"{what} was not found or is not visible in your scope.",
                         "Check the reference, or ask an administrator about your access scope.", 404)


class Forbidden(BusinessError):
    def __init__(self, message: str, next_step: str | None = None) -> None:
        super().__init__("FORBIDDEN", message, next_step or "Ask an administrator for the required permission.", 403)


class ValidationFailed(BusinessError):
    def __init__(self, message: str, details: list[dict[str, Any]] | None = None,
                 next_step: str | None = None) -> None:
        super().__init__("VALIDATION_FAILED", message, next_step or "Correct the highlighted fields and retry.",
                         400, details)


class InvalidTransition(BusinessError):
    def __init__(self, message: str, next_step: str | None = None) -> None:
        super().__init__("INVALID_TRANSITION", message, next_step, 409)


class VersionMismatch(BusinessError):
    def __init__(self) -> None:
        super().__init__("VERSION_MISMATCH", "This record was changed by someone else.",
                         "Reload the record and apply your change again.", 412)


def envelope(code: str, message: str, correlation_id: str | None, next_step: str | None = None,
             details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "next_step": next_step,
                      "correlation_id": correlation_id, "details": details or []}}
