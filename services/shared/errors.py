from datetime import datetime, timezone

from flask import jsonify, g, request


class ApiError(Exception):
    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def trace_id():
    return getattr(g, "trace_id", None) or request.headers.get("TraceId") or request.headers.get("X-Request-Id")


def error_response(error):
    payload = {
        "code": error.code,
        "message": error.message,
        "details": error.details,
        "traceId": trace_id(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = jsonify(payload)
    response.status_code = error.status_code
    return response


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return error_response(error)

    @app.errorhandler(404)
    def handle_not_found(_error):
        return error_response(ApiError(404, "not_found", "Resource not found"))

    @app.errorhandler(405)
    def handle_method_not_allowed(_error):
        return error_response(ApiError(405, "method_not_allowed", "Method not allowed"))

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        app.logger.exception("unexpected_error", extra={"error": str(error)})
        return error_response(ApiError(500, "internal_error", "Unexpected server error"))

