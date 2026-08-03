# Controlled Kafka DLQ replay

Replay only after the handler defect is corrected and the aggregate state is verified.
Idempotence is preserved by the original internal `eventId`.

1. Inspect the source-specific topic `<source-topic>.dlq` and record its partition and offsets.
2. Pause the affected service consumer group.
3. Extract `originalPayload` from each selected DLQ record; do not generate a new event ID.
4. Publish that payload to `originalTopic` with `aggregateId` as the message key.
5. Resume the consumer and confirm `processed_events`, aggregate state, Outbox state, and audit state.
6. Retain the DLQ record and the operator evidence; DLQ data is not automatically deleted.

Example inspection command:

```powershell
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic commande-passee.v1.dlq --from-beginning --property print.key=true
```
