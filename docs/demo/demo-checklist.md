# Demo checklist

## Before presentation

- [ ] Docker Desktop is running with enough memory for the full stack.
- [ ] Ports 3000, 3306, 6379, 8080, 8081, 8282, 9090, 16686, and 29092 are free.
- [ ] Word is closed so it does not lock the report if you need to open it.
- [ ] `.env` exists and local secrets are not shown on screen.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-reset.ps1 -Force`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight`.
- [ ] Verify `HLR_ENABLED=false`, `HLR_FORCE_FAILURE=false`, and `PAYMENT_GATEWAY_FORCE_REFUSAL=false`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance` once.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation` once.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Replay` once.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Dlq` once.
- [ ] Run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability` once.
- [ ] Confirm `docker image inspect cantelcox-test:phase2` succeeds (the first `-Step Replay` builds it).
- [ ] Open one Jaeger trace of `POST /v1/orders` and confirm it contains the `publish` and `consume` spans of all four services.
- [ ] Confirm Grafana `CanTelcoX Golden Signals` has traffic and latency panels populated.
- [ ] Confirm Grafana `CanTelcoX Event-Driven` shows consumer lag, Outbox backlog and saga panels.

## During presentation

- [ ] `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight`
  Expected: Compose config is valid, required containers are healthy, Gateway and Hub health are `UP`.
- [ ] Show slide 1 and give the Phase 1 to Phase 2 introduction.
- [ ] `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance`
  Expected: `HTTP 202`, `Location`, `EN_COURS`, same replayed `orderId`, final `CONFIRMEE`.
- [ ] Point to the printed order row, `saga_state`, `outbox_events`, `processed_events`, and audit records.
- [ ] Show the Jaeger trace of the order: one trace, `publish` and `consume` spans across the four services.
- [ ] `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation`
  Expected: billing service is recreated only once each way, final order state is `ANNULEE`, nominal payment flag is restored.
- [ ] `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Replay`
  Expected: identical state before and after, and `DUPLICATE` in the saga transition counters.
- [ ] `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Dlq`
  Expected: a record in `paiement-autorise.v1.dlq` with `attempts=3`, and the consumer still running.
- [ ] `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability`
  Expected: `2 passed, 2 deselected`.
- [ ] Show Jaeger, Grafana, and Prometheus links with `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Links -OpenDashboards`.
- [ ] Show the `CanTelcoX Event-Driven` dashboard, then the comparison table in `docs/demo/mesures-et-gains.md`.
- [ ] Close with slide 5 and the measured results plus honest limitations.

## Fallback actions

- [ ] If nominal order fails, run `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight`, check service health, then rerun only `-Step Acceptance`.
- [ ] If compensation fails, restore nominal with `PAYMENT_GATEWAY_FORCE_REFUSAL=false` and `docker compose -p cantelcox-phase2full up -d --force-recreate --wait svc-usage-facturation`, then show the saved evidence.
- [ ] If PortabilityHub fails, show `http://localhost:8282/actuator/health` and the saved evidence under `docs/evidence/phase2/portability/` if present.
- [ ] If Jaeger is empty, use the audit output from `-Step Acceptance` or `-Step Evidence` to show `trace_id`, `saga_id`, and `correlation_id`.
- [ ] If Grafana is empty, use Prometheus `up` and the raw performance evidence.

## After presentation

- [ ] Restore nominal environment values with `powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight`.
- [ ] Save screenshots and any new evidence you used.
- [ ] Stop the stack only if required by the lab machine policy: `docker compose -p cantelcox-phase2full down`.

