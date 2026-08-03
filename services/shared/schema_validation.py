from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


CONTRACTS_ROOT = Path(__file__).resolve().parents[2] / "contracts" / "events"


def load_event_schema(event_type: str, version: int = 1) -> dict:
    path = CONTRACTS_ROOT / event_type / f"v{version}.json"
    if not path.is_file():
        raise ValueError(f"No schema for {event_type} v{version}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_event(document: dict) -> None:
    event_type = document.get("eventType")
    version = document.get("eventVersion")
    schema = load_event_schema(event_type, version)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(document)
