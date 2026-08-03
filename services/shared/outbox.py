from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from services.shared.events import EventEnvelope
from services.shared.event_metrics import EVENT_RETRIES, OUTBOX_OLDEST_AGE, OUTBOX_PENDING


@dataclass(frozen=True)
class OutboxRecord:
    event_id: str
    event_type: str
    aggregate_id: str
    payload: dict
    attempt_count: int
    lock_token: str


class MysqlOutboxRepository:
    def insert(self, cursor, envelope: EventEnvelope) -> None:
        cursor.execute(
            """
            INSERT INTO outbox_events
              (event_id, aggregate_id, aggregate_type, event_type, event_version,
               payload, occurred_at, status, attempt_count, next_attempt_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', 0, UTC_TIMESTAMP(6))
            """,
            (
                envelope.eventId,
                envelope.aggregateId,
                envelope.aggregateType,
                envelope.eventType,
                envelope.eventVersion,
                json.dumps(envelope.to_dict(), separators=(",", ":")),
                _mysql_datetime(envelope.occurredAt),
            ),
        )

    def claim_pending(self, cursor, batch_size: int = 100, lease_seconds: int = 30) -> list[OutboxRecord]:
        if not 1 <= batch_size <= 1000:
            raise ValueError("batch_size must be between 1 and 1000")
        lock_token = str(uuid4())
        cursor.execute(
            f"""
            SELECT id
            FROM outbox_events
            WHERE (status = 'PENDING' AND next_attempt_at <= UTC_TIMESTAMP(6))
               OR (status = 'PUBLISHING' AND locked_until < UTC_TIMESTAMP(6))
            ORDER BY occurred_at, id
            LIMIT {batch_size}
            FOR UPDATE SKIP LOCKED
            """
        )
        ids = [row["id"] for row in cursor.fetchall()]
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        cursor.execute(
            f"""
            UPDATE outbox_events
            SET status='PUBLISHING', lock_token=%s,
                locked_until=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND)
            WHERE id IN ({placeholders})
            """,
            (lock_token, lease_seconds, *ids),
        )
        cursor.execute(
            """
            SELECT event_id, event_type, aggregate_id, payload, attempt_count
            FROM outbox_events WHERE lock_token=%s ORDER BY occurred_at, id
            """,
            (lock_token,),
        )
        return [
            OutboxRecord(
                event_id=row["event_id"],
                event_type=row["event_type"],
                aggregate_id=row["aggregate_id"],
                payload=json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"],
                attempt_count=row["attempt_count"],
                lock_token=lock_token,
            )
            for row in cursor.fetchall()
        ]

    def mark_published(self, cursor, event_id: str, lock_token: str) -> None:
        cursor.execute(
            """
            UPDATE outbox_events
            SET status='PUBLISHED', published_at=UTC_TIMESTAMP(6), last_error=NULL,
                lock_token=NULL, locked_until=NULL
            WHERE event_id=%s AND status='PUBLISHING' AND lock_token=%s
            """,
            (event_id, lock_token),
        )

    def mark_failed(self, cursor, event_id: str, lock_token: str, error: str, backoff_seconds: int) -> None:
        cursor.execute(
            """
            UPDATE outbox_events
            SET status='PENDING', attempt_count=attempt_count + 1,
                last_error=%s,
                next_attempt_at=DATE_ADD(UTC_TIMESTAMP(6), INTERVAL %s SECOND),
                lock_token=NULL, locked_until=NULL
            WHERE event_id=%s AND status='PUBLISHING' AND lock_token=%s
            """,
            (error[:2000], backoff_seconds, event_id, lock_token),
        )


class OutboxRelay:
    """Lease rows in MySQL, publish outside SQL transactions, then acknowledge."""

    def __init__(self, connection_factory: Callable, publisher, repository=None, service_name="unknown"):
        self.connection_factory = connection_factory
        self.publisher = publisher
        self.repository = repository or MysqlOutboxRepository()
        self.service_name = service_name

    def publish_batch(self, batch_size: int = 100) -> int:
        records = run_in_transaction(
            self.connection_factory,
            lambda cursor: self.repository.claim_pending(cursor, batch_size),
        )
        for record in records:
            try:
                self.publisher.publish(record.event_type, record.aggregate_id, record.payload)
            except Exception as exc:
                EVENT_RETRIES.labels(self.service_name, "outbox", record.event_type).inc()
                run_in_transaction(
                    self.connection_factory,
                    lambda cursor, r=record, e=exc: self.repository.mark_failed(
                        cursor, r.event_id, r.lock_token, str(e), min(2 ** r.attempt_count, 30)
                    ),
                )
                continue
            run_in_transaction(
                self.connection_factory,
                lambda cursor, r=record: self.repository.mark_published(
                    cursor, r.event_id, r.lock_token
                ),
            )
        self._update_metrics()
        return len(records)

    def _update_metrics(self):
        def query(cursor):
            cursor.execute(
                "SELECT COUNT(*) AS pending, COALESCE(TIMESTAMPDIFF(MICROSECOND,MIN(occurred_at),UTC_TIMESTAMP(6))/1000000,0) AS oldest FROM outbox_events WHERE status!='PUBLISHED'"
            )
            return cursor.fetchone()

        row = run_in_transaction(self.connection_factory, query)
        OUTBOX_PENDING.labels(self.service_name).set(row["pending"])
        OUTBOX_OLDEST_AGE.labels(self.service_name).set(float(row["oldest"]))


def run_in_transaction(connection_factory: Callable, operation):
    with connection_factory() as connection:
        try:
            with connection.cursor() as cursor:
                result = operation(cursor)
            connection.commit()
            return result
        except Exception:
            connection.rollback()
            raise


def _mysql_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)
