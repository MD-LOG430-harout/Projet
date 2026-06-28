import time
import uuid

from flask import g, request


def register_request_hooks(app, service_name):
    @app.before_request
    def before_request():
        g.started_at = time.perf_counter()
        g.trace_id = request.headers.get("TraceId") or request.headers.get("X-Request-Id") or str(uuid.uuid4())

    @app.after_request
    def after_request(response):
        duration_ms = int((time.perf_counter() - g.started_at) * 1000)
        response.headers["TraceId"] = g.trace_id
        response.headers["X-Request-Id"] = g.trace_id
        app.logger.info(
            "http_request",
            extra={
                "service": service_name,
                "traceId": g.trace_id,
                "method": request.method,
                "path": request.path,
                "statusCode": response.status_code,
                "durationMs": duration_ms,
            },
        )
        return response

