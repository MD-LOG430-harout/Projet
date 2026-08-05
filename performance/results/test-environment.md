# Test environment

- Measurement date: 2026-08-05 11:39-11:45 America/Toronto (15:39-15:45 UTC).
- Host OS: Windows; exact edition/version, CPU, and physical memory were unavailable because WMI/systeminfo access was denied. This is a material reproducibility limitation.
- Docker Engine: 29.4.3; Docker Compose: 5.1.3.
- Source commit: `535fd6a6f378eb369d139755a07cfb8a36eca625` with a dirty worktree. Performance files are new; unrelated pre-existing edits were preserved.
- Service images: matching local `cantelcox-phase2full-*` images retagged as `projet-*` because a clean rebuild failed while downloading `cryptography==43.0.0`.
- Instances: one container per application service; two Gunicorn workers and four threads per container from `.env.example`.
- Kafka: Apache Kafka 3.8.0, KRaft, three partitions per business/DLQ topic, replication factor 1. Consumer groups: `svc-conformite-audit`, `svc-lignes-services`, `svc-commandes-activations`, `svc-usage-facturation`.
- MySQL: 8.4 container. Redis: `redis:7-alpine` (runtime log reported 7.4.10). NGINX: 1.27-alpine.
- Observability: Prometheus 2.53.0, Grafana 11.1.0, Jaeger 1.60, OpenTelemetry Collector 0.107.0.
- k6: Grafana k6 0.54.0 container.
- Initial database state: new Compose volumes and schema bootstrap; no pre-existing business rows. A first one-shot bootstrap lost its MySQL startup race and was rerun successfully.
- Reset method: new project-scoped volumes for this campaign. The committed reset helper only clears Redis and deliberately does not delete business data.
- Test durations: acceptance 10 s at 20 offered ops/s; nominal saga 20 iterations/5 VUs; cache 10 s/20 VUs; progressive probe six 5 s stages.
- Known limitations: no host CPU/RAM sample, no long-duration steady stage, no per-stage Prometheus export, no compensation/replay/DLQ/LB failure campaign, and no automated Grafana/Jaeger screenshots.
