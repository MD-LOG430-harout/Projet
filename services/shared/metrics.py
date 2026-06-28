from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from flask import Response, request


REQUEST_COUNT = Counter(
    "cantelcox_http_requests_total",
    "HTTP requests",
    ["service", "method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "cantelcox_http_request_duration_seconds",
    "HTTP request latency",
    ["service", "method", "path"],
)


def register_metrics(app, service_name):
    @app.before_request
    def start_metrics_timer():
        request._metrics_timer = REQUEST_LATENCY.labels(service_name, request.method, request.path).time()
        request._metrics_timer.__enter__()

    @app.after_request
    def record_metrics(response):
        timer = getattr(request, "_metrics_timer", None)
        if timer:
            timer.__exit__(None, None, None)
        REQUEST_COUNT.labels(service_name, request.method, request.path, response.status_code).inc()
        return response

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

