from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from os import environ
from typing import MutableMapping

from opentelemetry.propagate import extract, inject


TRACEPARENT_PATTERN = re.compile(
    r"^00-(?P<trace_id>[0-9a-f]{32})-(?P<span_id>[0-9a-f]{16})-(?P<flags>[0-9a-f]{2})$"
)


@dataclass(frozen=True)
class OtelSettings:
    service_name: str
    endpoint: str
    enabled: bool

    @classmethod
    def from_env(cls, service_name: str) -> "OtelSettings":
        return cls(
            service_name=service_name,
            endpoint=environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318"),
            enabled=environ.get("OTEL_SDK_DISABLED", "true").lower() != "true",
        )


def initialize_tracing(settings: OtelSettings):
    """Install an OTLP tracer provider; application wiring is done per service."""
    if not settings.enabled:
        return None
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": settings.service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{settings.endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    return provider


def parse_traceparent(value: str | None) -> dict[str, str] | None:
    if not value:
        return None
    match = TRACEPARENT_PATTERN.fullmatch(value.strip().lower())
    if not match or match.group("trace_id") == "0" * 32 or match.group("span_id") == "0" * 16:
        return None
    return match.groupdict()


def inject_traceparent(headers: MutableMapping[str, str], traceparent: str) -> None:
    if parse_traceparent(traceparent) is None:
        raise ValueError("traceparent must be a valid W3C version 00 header")
    headers["traceparent"] = traceparent.lower()


def extract_context(headers):
    return extract(headers)


def inject_context(headers: MutableMapping[str, str], context=None) -> None:
    inject(headers, context=context)


def traceparent_from_trace_id(trace_id: str, sampled: bool = True) -> str:
    candidate = trace_id.lower().replace("-", "")
    if not re.fullmatch(r"[0-9a-f]{32}", candidate) or candidate == "0" * 32:
        raise ValueError("trace_id must contain 32 non-zero hexadecimal characters")
    span_id = secrets.token_hex(8)
    return f"00-{candidate}-{span_id}-{'01' if sampled else '00'}"
