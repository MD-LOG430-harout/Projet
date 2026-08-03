import json
import os
import time
from uuid import uuid4

import pymysql
import pytest
from jsonschema import ValidationError
from kafka import KafkaConsumer, KafkaProducer
from kafka.structs import TopicPartition

from services.shared.events import EVENT_TOPICS, EventEnvelope
from services.shared.kafka import KafkaEnvelopePublisher, handle_record
from services.shared.outbox import MysqlOutboxRepository, OutboxRelay, run_in_transaction
from services.shared.processed_events import DuplicateEvent, MysqlProcessedEventRepository


MYSQL_HOST = os.getenv("INCREMENT0_MYSQL_HOST", "127.0.0.1")
KAFKA_BOOTSTRAP = os.getenv("INCREMENT0_KAFKA_BOOTSTRAP", "127.0.0.1:29092")
MYSQL_PASSWORD = os.getenv("INCREMENT0_MYSQL_PASSWORD", os.getenv("MYSQL_PASSWORD", "cantelcox"))


def connect(database="commandes_activations"):
    return pymysql.connect(
        host=MYSQL_HOST,
        user="cantelcox",
        password=MYSQL_PASSWORD,
        database=database,
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
    )


def envelope(event_id=None):
    return EventEnvelope.create(
        event_type="CommandePassee",
        aggregate_id=f"cmd-{uuid4()}",
        aggregate_type="Commande",
        payload={
            "idCommande": f"cmd-{uuid4()}",
            "idClient": "cli-1",
            "idOffre": "offre-1",
            "montant": 10.0,
            "devise": "CAD",
        },
        trace_id="0123456789abcdef0123456789abcdef",
        correlation_id="verification-increment0",
        saga_id=str(uuid4()),
        event_id=event_id,
    )


def test_migration_inventory_and_mysql_definitions():
    expected_outbox = {"commandes_activations", "usage_facturation", "lignes_services"}
    expected_processed = expected_outbox | {"conformite_audit"}
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT table_schema AS schema_name, table_name AS object_name, engine AS storage_engine
                   FROM information_schema.tables
                   WHERE table_schema IN ('clients_identite','conformite_audit','catalogue_offres',
                     'lignes_services','commandes_activations','usage_facturation')
                     AND table_name IN ('outbox_events','processed_events')"""
            )
            rows = cursor.fetchall()
            assert {r["schema_name"] for r in rows if r["object_name"] == "outbox_events"} == expected_outbox
            assert {r["schema_name"] for r in rows if r["object_name"] == "processed_events"} == expected_processed
            assert all(r["storage_engine"] == "InnoDB" for r in rows)
            cursor.execute("SHOW CREATE TABLE outbox_events")
            ddl = cursor.fetchone()["Create Table"]
            assert "json not null" in ddl.lower()
            assert "primary key (`id`)" in ddl.lower()
            assert "UNIQUE KEY `uq_outbox_event_id`" in ddl
            assert "KEY `idx_outbox_pending`" in ddl
            assert "datetime(6)" in ddl.lower()
            assert "enum('PENDING','PUBLISHING','PUBLISHED')".lower() in ddl.lower()
            cursor.execute("SHOW CREATE TABLE processed_events")
            processed_ddl = cursor.fetchone()["Create Table"]
            assert "primary key (`event_id`)" in processed_ddl.lower()
            assert "timestamp(6)" in processed_ddl.lower()
            assert "KEY `idx_processed_type_time`" in processed_ddl


def test_business_and_outbox_atomicity_and_rollback():
    repository = MysqlOutboxRepository()
    committed = envelope()
    rolled_back = envelope()
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS increment0_probe (id VARCHAR(120) PRIMARY KEY) ENGINE=InnoDB")
        connection.commit()

    def commit_operation(cursor):
        cursor.execute("INSERT INTO increment0_probe (id) VALUES (%s)", (committed.aggregateId,))
        repository.insert(cursor, committed)

    run_in_transaction(connect, commit_operation)
    connection = connect()
    try:
        with pytest.raises(RuntimeError):
            def rollback_operation(cursor):
                cursor.execute("INSERT INTO increment0_probe (id) VALUES (%s)", (rolled_back.aggregateId,))
                repository.insert(cursor, rolled_back)
                raise RuntimeError("rollback")
            run_in_transaction(connect, rollback_operation)
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM increment0_probe WHERE id IN (%s,%s)", (committed.aggregateId, rolled_back.aggregateId))
            assert cursor.fetchone()["n"] == 1
            cursor.execute("SELECT COUNT(*) AS n FROM outbox_events WHERE event_id IN (%s,%s)", (committed.eventId, rolled_back.eventId))
            assert cursor.fetchone()["n"] == 1
    finally:
        connection.close()


def test_processed_event_and_effect_share_transaction():
    event_id = str(uuid4())
    repository = MysqlProcessedEventRepository()
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE IF NOT EXISTS increment0_effect (event_id CHAR(36) PRIMARY KEY) ENGINE=InnoDB")
        connection.commit()

    def operation(cursor):
        repository.reserve(cursor, event_id, "CommandePassee")
        cursor.execute("INSERT INTO increment0_effect (event_id) VALUES (%s)", (event_id,))

    run_in_transaction(connect, operation)
    with pytest.raises(DuplicateEvent):
        run_in_transaction(connect, operation)


def producer():
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        acks="all",
        enable_idempotence=True,
        retries=5,
        max_in_flight_requests_per_connection=1,
    )


def consumer(group):
    return KafkaConsumer(
        EVENT_TOPICS["CommandePassee"],
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id=group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        key_deserializer=lambda value: value.decode(),
        value_deserializer=lambda value: json.loads(value),
    )


def next_matching(client, event_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        records = client.poll(timeout_ms=500)
        for batch in records.values():
            for record in batch:
                if record.value.get("eventId") == event_id:
                    return record
    raise AssertionError(f"event {event_id} not received")


def test_live_kafka_key_validation_commit_order_and_stable_retry():
    document = envelope()
    raw_producer = producer()
    publisher = KafkaEnvelopePublisher(raw_producer)
    client = consumer(f"increment0-{uuid4()}")
    try:
        publisher.publish(document.eventType, document.aggregateId, document.to_dict())
        first = next_matching(client, document.eventId)
        assert first.key == document.aggregateId
        partition = TopicPartition(first.topic, first.partition)
        assert client.committed(partition) is None
        handled = []
        handle_record(client, first, handled.append)
        assert handled[0]["eventId"] == document.eventId
        assert client.committed(partition) == first.offset + 1
        publisher.publish(document.eventType, document.aggregateId, document.to_dict())
        second = next_matching(client, document.eventId)
        assert second.value["eventId"] == first.value["eventId"]

        invalid = dict(document.to_dict())
        invalid.pop("aggregateId")
        metadata = raw_producer.send(
            document.topic,
            key=document.aggregateId.encode(),
            value=json.dumps(invalid).encode(),
        ).get(timeout=10)
        bad = next_matching(client, document.eventId)
        before = client.committed(TopicPartition(metadata.topic, metadata.partition))
        with pytest.raises(ValidationError):
            handle_record(client, bad, handled.append)
        assert client.committed(TopicPartition(metadata.topic, metadata.partition)) == before
    finally:
        client.close()
        raw_producer.close()


def test_outbox_relay_ack_failure_retry_and_two_poller_exclusion():
    document = envelope()
    repository = MysqlOutboxRepository()
    run_in_transaction(connect, lambda cursor: cursor.execute("DELETE FROM outbox_events"))
    run_in_transaction(connect, lambda cursor: repository.insert(cursor, document))
    first = run_in_transaction(connect, lambda cursor: repository.claim_pending(cursor, 1))
    second = run_in_transaction(connect, lambda cursor: repository.claim_pending(cursor, 1))
    assert len(first) == 1
    assert second == []
    run_in_transaction(
        connect,
        lambda cursor: repository.mark_failed(cursor, first[0].event_id, first[0].lock_token, "broker down", 0),
    )

    raw_producer = producer()
    client = consumer(f"increment0-outbox-{uuid4()}")
    try:
        relay = OutboxRelay(connect, KafkaEnvelopePublisher(raw_producer), repository)
        assert relay.publish_batch(1) == 1
        received = next_matching(client, document.eventId)
        assert received.value["eventId"] == document.eventId
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT status, published_at, attempt_count FROM outbox_events WHERE event_id=%s", (document.eventId,))
                row = cursor.fetchone()
                assert row["status"] == "PUBLISHED"
                assert row["published_at"] is not None
                assert row["attempt_count"] == 1
    finally:
        client.close()
        raw_producer.close()
