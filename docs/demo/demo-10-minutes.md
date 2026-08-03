# CanTelcoX Phase 2 - 10-minute live demo

Main rule: use the mock HLR path for the nominal scenario. Do not present real
free5GC provisioning as successful; the supplied WebConsole currently returns an
incompatible subscriber representation and the adapter correctly compensates with
`SUBSCRIBER_CONFLICT`.

## Before the teacher arrives

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-reset.ps1 -Force
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

Open these tabs:

- Swagger: <http://localhost:8081>
- Jaeger: <http://localhost:16686>
- Grafana: <http://localhost:3000>
- Prometheus: <http://localhost:9090>
- PortabilityHub health: <http://localhost:8282/actuator/health>

## Part 1 - Introduction, maximum 1 minute

Show slide 1 only.

Say:

> In Phase 1, CanTelcoX mainly coordinated services with synchronous REST calls.
> Phase 2 keeps the same six services and the same implemented use cases, but
> adapts the collaboration model. A public request is accepted quickly with
> `202 Accepted`; the local service writes its business row and an Outbox event
> in MySQL, then Kafka carries the saga steps asynchronously. The main additions
> are Kafka, Transactional Outbox, a choreographed saga, idempotent consumers,
> retry and DLQ handling, OpenTelemetry traces, metrics, audit, and the supplied
> synchronous PortabilityHub.

Do not spend more than 60 seconds on slides.

## Part 2 - Nominal order saga, about 4 minutes

Run:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
```

Point to the output:

- `POST /v1/orders`
- `HTTP 202`
- `Location: /v1/orders/{orderId}/status`
- returned `orderId`, `sagaId`, and initial status `EN_COURS`
- replay with the same `Idempotency-Key` returns the same `orderId`
- polling `GET /v1/orders/{orderId}/status` reaches `CONFIRMEE`

Expected flow:

```text
CommandePassee
-> PaiementAutorise
-> LigneActivee
-> CommandeConfirmee
```

The same script also prints useful database evidence:

- `commandes_activations.orders`
- `commandes_activations.saga_state`
- producer `outbox_events`
- consumer `processed_events`
- `conformite_audit.audit_events`

Say:

> The `202` is acceptance, not completion. There is no central orchestrator:
> billing consumes `CommandePassee`, lines consumes `PaiementAutorise`, and the
> order service consumes the resulting facts until it reaches a terminal state.
> Outbox publication is at-least-once, and duplicate effects are blocked by
> `processed_events` plus aggregate state guards.

## Part 3 - Compensation, about 2 minutes

Fastest reliable scenario:

```text
CommandePassee
-> PaiementRefuse
-> CommandeAnnulee
```

Run:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
```

What it does:

- sets `PAYMENT_GATEWAY_FORCE_REFUSAL=true`;
- restarts only `svc-usage-facturation`;
- creates a new order;
- shows terminal status `ANNULEE`;
- prints order, saga, Outbox, processed event, and audit rows;
- restores `PAYMENT_GATEWAY_FORCE_REFUSAL=false`;
- restarts only `svc-usage-facturation` again.

Say:

> A business refusal is not a technical DLQ case. It is a domain event,
> `PaiementRefuse`, consumed by the order service, which emits
> `CommandeAnnulee`. The demo restores the nominal payment configuration before
> moving on.

Fallback if this command fails: run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability`
and show the rejected portability compensation scenario instead.

## Part 4 - PortabilityHub, about 1 minute

Run:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

Expected result:

```text
2 passed, 2 deselected
```

Show:

- synchronous REST initiation to the supplied Hub;
- Hub `orderId`;
- HTTP callback;
- mapping from actual Hub statuses to internal facts;
- duplicate callback idempotence if time allows.

Use only these actual Hub statuses:

```text
pending_out_validation
approved
rejected
port_completed
cancelled
```

Say:

> The supplied Hub is synchronous for initiation and HTTP-based for notifications.
> It is not one of our internal Kafka producers. `port_completed` maps to
> `NumeroPorte`; `rejected` and `cancelled` map to `PortabiliteEchouee`.

## Part 5 - Observability, about 1 minute

Run:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Links -OpenDashboards
```

Jaeger:

- open <http://localhost:16686>;
- search service `svc-commandes-activations`;
- if sparse, also search `svc-usage-facturation`, `svc-lignes-services`, and
  `svc-conformite-audit`;
- show the trace path that is available: REST, local handling, Outbox, Kafka
  publish, Kafka consume, service handler.

Grafana:

- open <http://localhost:3000>;
- open folder `CanTelcoX`;
- open dashboard `CanTelcoX Golden Signals`;
- show traffic, errors, latency P95/P99, CPU, and memory.

Prometheus fallback queries:

```promql
sum(rate(cantelcox_http_requests_total[1m])) by (service)
histogram_quantile(0.95, sum(rate(cantelcox_http_request_duration_seconds_bucket[5m])) by (le, service))
```

Event-specific evidence to mention from the saved validation:

- saga duration;
- produced and consumed events;
- Outbox pending rows;
- Kafka lag;
- errors and DLQ tests.

If no trace appears live, show `trace_id`, `saga_id`, and `correlation_id` in the
audit output and state that the visual trace capture is not available in that
moment.

## Part 6 - Conclusion, maximum 1 minute

Show slide 4.

Say:

> Phase 2 is implemented for the existing Phase 1 use cases: accepted REST
> commands, Kafka propagation, Transactional Outbox, choreographed saga,
> idempotent consumers, retry/DLQ evidence, PortabilityHub integration,
> append-only audit, traces, and metrics. The verified suite has 97 passed,
> 0 failed, and 12 skipped. Measured nominal saga P95 is 2.0 s, compensation P95
> is 2.9543 s, availability in the nominal mixed test is 100%, Kafka lag after
> drain is 0, and pending Outbox rows after drain are 0. The honest limits are
> important: order acceptance P95 was 810 ms, so the 250 ms target was not met;
> throughput was 489.91 req/s, so the 1000 ops/s target was not met; and real
> free5GC success was not validated.

