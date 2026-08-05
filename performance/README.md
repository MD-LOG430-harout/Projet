# Phase 2 architecture verification

This directory contains black-box k6 tests and evidence collectors for report Section 10. The repository's public command endpoint is `/v1/orders` (not `/v1/commandes`), so all tests use the implemented API and generate an isolated authenticated customer in `setup()`.

## Prerequisites

Copy `.env.example` to `.env`, start the stack, and wait for health:

```powershell
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts\wait-compose-health.ps1 -TimeoutSeconds 300
```

If using the official container runner on this repository's default Compose project/network:

```powershell
$mount = "${PWD}\performance:/performance"
docker run --rm --network projet_default -v $mount -w /performance grafana/k6:0.54.0 run -e BASE_URL=http://api-gateway --summary-trend-stats "avg,min,med,max,p(90),p(95),p(99)" --summary-export results/phase2-acceptance-summary.json k6/phase2-acceptance.js
docker run --rm --network projet_default -v $mount -w /performance grafana/k6:0.54.0 run -e BASE_URL=http://api-gateway --summary-trend-stats "avg,min,med,max,p(90),p(95),p(99)" --summary-export results/phase2-saga-summary.json k6/phase2-saga-convergence.js
docker run --rm --network projet_default -v $mount -w /performance grafana/k6:0.54.0 run -e BASE_URL=http://api-gateway --summary-export results/cache-verification.json k6/phase2-cache.js
docker run --rm --network projet_default -v $mount -w /performance grafana/k6:0.54.0 run -e BASE_URL=http://api-gateway --summary-export results/phase2-load-stages-summary.json k6/phase2-load-stages.js
```

All rates/durations are configurable with environment values shown in each script. The committed progressive result used `STAGE_DURATION=5s`; use the default 30-second stages for the final VM campaign.

## Compensation

Use a test-only Compose override or environment recreation so only `svc-lignes-services` receives `HLR_FORCE_FAILURE=true`, then run:

```powershell
docker compose up -d --force-recreate svc-lignes-services
docker run --rm --network projet_default -v $mount -w /performance grafana/k6:0.54.0 run -e BASE_URL=http://api-gateway --summary-trend-stats "avg,min,med,max,p(90),p(95),p(99)" --summary-export results/phase2-compensation-summary.json k6/phase2-compensation.js
```

Verify refund, released line/MSISDN, audit, deduplication, and DLQ directly in MySQL/Kafka before claiming compensation coherence. The current result file is explicitly `not_executed`.

## Consumer recovery

Run `phase2-failure-recovery.js` for two minutes. In another terminal run `bash performance/scripts/collect-evidence.sh`, stop the real consumer using `stop-consumer.sh`, keep load running for 30 seconds, then invoke `start-consumer.sh`. Preserve the CSV only after lag returns to its baseline and all created order IDs are terminal.

## Duplicate and DLQ

Capture an already-published JSON event exactly, record before-counts in `processed_events`, payments, lines, activations, and producer Outbox, then run:

```bash
bash performance/scripts/replay-event.sh performance/results/captured-event.json commande-passee.v1
```

For DLQ, publish a schema-invalid event with a unique non-business aggregate identifier, inspect `<topic>.dlq` with `kafka-console-consumer.sh`, and record retained headers/reason. Never change its `eventId` for the duplicate test.

## Load balancing

```powershell
docker compose up -d --scale svc-commandes-activations=2
docker compose restart api-gateway
# Run phase2-load-balancing.js, stop exactly one replica by its resolved name, then let the test finish.
docker ps --filter "name=svc-commandes-activations" --format "{{.Names}}"
docker stop <one-resolved-replica-name>
```

Record response P95/error rate before and after the stop. Current application responses do not expose instance identity, so use per-container structured logs to prove distribution.

## Evidence screenshots

Use the exact UTC campaign range recorded in `test-environment.md` (2026-08-05 15:39-15:45 UTC) for the measurements in this directory. Open Grafana at `http://localhost:3000` and export/capture the provisioned CanTelcoX dashboard panels for overview, HTTP latency, Kafka lag, Outbox, Golden Signals, and recovery. Open Jaeger at `http://localhost:16686`, filter by each participating service and the same time range, select one confirmed saga trace, and save `jaeger-nominal-saga.png`. A compensated trace must come from a separately executed failure campaign; do not reuse a nominal trace. Filter container JSON logs by the selected trace ID and capture the matching `sagaId`, `eventId`, and correlation identifiers as `logs-trace-correlation.png`.

No screenshots are committed because browser automation was unavailable and no placeholder image should be mistaken for evidence.
