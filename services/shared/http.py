import time
import uuid
import hashlib

from flask import g, request
from services.shared.tracing import parse_traceparent, traceparent_from_trace_id
from opentelemetry import trace
from opentelemetry.propagate import extract


def register_request_hooks(app, service_name):
    @app.before_request
    def before_request():
        g.started_at = time.perf_counter()
        incoming = parse_traceparent(request.headers.get("traceparent"))
        raw_fallback = request.headers.get("TraceId") or request.headers.get("X-Request-Id") or uuid.uuid4().hex
        compact = raw_fallback.replace("-", "").lower()
        fallback = compact if len(compact) == 32 and all(char in "0123456789abcdef" for char in compact) else hashlib.sha256(raw_fallback.encode("utf-8")).hexdigest()[:32]
        legacy_trace_id = request.headers.get("TraceId") or request.headers.get("X-Request-Id")
        g.trace_id = incoming["trace_id"] if incoming else legacy_trace_id or fallback[:32].lower()
        g.w3c_trace_id = incoming["trace_id"] if incoming else fallback[:32].lower()
        g.traceparent = request.headers.get("traceparent") if incoming else traceparent_from_trace_id(g.w3c_trace_id)
        # Anchor the span on the business trace id when the caller sent no W3C header.
        # The Outbox relay publishes later, in another thread, and can only rebuild a
        # traceparent from the envelope traceId; sharing the id keeps REST, publish and
        # consume inside a single Jaeger trace.
        parent_context = extract(request.headers) if incoming else extract({"traceparent": g.traceparent})
        g.otel_span_context = trace.get_tracer(service_name).start_as_current_span(
            f"{request.method} {request.path}", context=parent_context
        )
        g.otel_span = g.otel_span_context.__enter__()

    @app.after_request
    def after_request(response):
        duration_ms = int((time.perf_counter() - g.started_at) * 1000)
        response.headers["TraceId"] = g.trace_id
        response.headers["X-Request-Id"] = g.trace_id
        response.headers["traceparent"] = getattr(g, "traceparent", traceparent_from_trace_id(g.w3c_trace_id))
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
        span = getattr(g, "otel_span", None)
        if span:
            span.set_attribute("http.request.method", request.method)
            span.set_attribute("http.route", request.path)
            span.set_attribute("http.response.status_code", response.status_code)
            g.otel_span_context.__exit__(None, None, None)
        return response
