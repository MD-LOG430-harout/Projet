from __future__ import annotations


class DuplicateEvent(Exception):
    pass


class MysqlProcessedEventRepository:
    def reserve(self, cursor, event_id: str, event_type: str) -> None:
        try:
            cursor.execute(
                "INSERT INTO processed_events (event_id, event_type) VALUES (%s, %s)",
                (event_id, event_type),
            )
        except Exception as exc:
            if getattr(exc, "args", [None])[0] == 1062:
                raise DuplicateEvent(event_id) from exc
            raise

