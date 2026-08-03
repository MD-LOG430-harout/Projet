# Demo troubleshooting

## 30-second rule

If a live step does not recover in 30 seconds, run the matching diagnostic below.
After one minute, switch to saved evidence under `docs/evidence/phase2/` and keep
the presentation moving. Do not debug code live.

## Unhealthy Kafka

```powershell
docker compose -p cantelcox-phase2full ps kafka
docker compose -p cantelcox-phase2full logs --since=3m kafka
docker compose -p cantelcox-phase2full up -d --force-recreate --wait kafka
```

Then rerun:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
```

## Unhealthy MySQL

```powershell
docker compose -p cantelcox-phase2full ps mysql
docker compose -p cantelcox-phase2full logs --since=3m mysql
docker compose -p cantelcox-phase2full exec -T mysql mysqladmin ping -h localhost
```

If it is a rehearsal and not the live presentation, use:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-reset.ps1 -Force
```

## No trace in Jaeger

```powershell
docker compose -p cantelcox-phase2full ps otel-collector jaeger
docker compose -p cantelcox-phase2full logs --since=3m otel-collector jaeger
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
```

Refresh <http://localhost:16686> after a few seconds. If spans still do not
appear, show the audit output from the script and explain the correlation with
`trace_id`, `saga_id`, and `correlation_id`.

## No metrics in Grafana

Open Prometheus first:

```powershell
Invoke-RestMethod http://localhost:9090/-/ready
```

Try:

```promql
up
sum(rate(cantelcox_http_requests_total[1m])) by (service)
```

In Grafana, use folder `CanTelcoX` and dashboard `CanTelcoX Golden Signals`.

## Order stuck in EN_COURS

```powershell
docker compose -p cantelcox-phase2full logs --since=3m svc-commandes-activations svc-usage-facturation svc-lignes-services
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Evidence
```

Common causes:

- `PAYMENT_GATEWAY_FORCE_REFUSAL` was left enabled;
- `HLR_ENABLED` or `HLR_FORCE_FAILURE` is not nominal;
- Kafka consumers were still starting when the order was created.

Restore nominal service configuration:

```powershell
$env:HLR_ENABLED='false'
$env:HLR_FORCE_FAILURE='false'
$env:PAYMENT_FORCE_REFUSAL='false'
$env:PAYMENT_GATEWAY_FORCE_REFUSAL='false'
$env:PAYMENT_GATEWAY_FORCE_FAILURE='false'
docker compose -p cantelcox-phase2full up -d --force-recreate --wait svc-lignes-services svc-usage-facturation
```

## Stale Outbox rows

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Evidence
docker compose -p cantelcox-phase2full logs --since=3m svc-commandes-activations svc-usage-facturation svc-lignes-services
```

Rows in `PUBLISHED` are normal and useful for the demo. A growing `PENDING` or
`FAILED` set usually means Kafka or an Outbox poller service is unhealthy.

## PortabilityHub callback failure

The Hub root page can show a Whitelabel 404. That is normal. Use:

```powershell
Invoke-RestMethod http://localhost:8282/actuator/health
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

Use only actual Hub statuses: `pending_out_validation`, `approved`, `rejected`,
`port_completed`, and `cancelled`.

## Payment refusal flag not applied

Check the effective container value:

```powershell
docker compose -p cantelcox-phase2full exec -T svc-usage-facturation printenv PAYMENT_GATEWAY_FORCE_REFUSAL
```

Apply without rebuilding:

```powershell
$env:PAYMENT_GATEWAY_FORCE_REFUSAL='true'
docker compose -p cantelcox-phase2full up -d --force-recreate --wait svc-usage-facturation
```

Restore:

```powershell
$env:PAYMENT_GATEWAY_FORCE_REFUSAL='false'
docker compose -p cantelcox-phase2full up -d --force-recreate --wait svc-usage-facturation
```

## Docker network name mismatch

The scripts assume project `cantelcox-phase2full`, so the test network is:

```text
cantelcox-phase2full_default
```

If you used another project name, pass it explicitly:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -ProjectName my-project -Step Preflight
```

## Missing test image

If `cantelcox-test:phase2` is missing, build it before the presentation using the
project's normal Docker test-image command. During the live demo, prefer the HTTP
scenario `-Step Acceptance` and saved evidence instead of rebuilding.

## Real free5GC limitation

Do not attempt to fix real free5GC during the demo. The verified honest result is
that login succeeds, `GET`/`POST` contract rules are respected, no `PUT` is used,
but the supplied WebConsole returns an incompatible representation and the saga
compensates with `SUBSCRIBER_CONFLICT`.


## Nouveaux steps de la soutenance 15 minutes

### `-Step Replay` echoue avec "No LigneActivee event found"

La commande de reference n'a pas de `LigneActivee` en base, en general parce que
la saga s'est terminee en `ANNULEE`. Relancer sans `-OrderId` : le step cree
alors sa propre commande nominale avant de rejouer l'evenement.

### `-Step Dlq` affiche "No DLQ record read back"

Le topic `.dlq` n'a pas encore recu le message. Attendre cinq secondes et
relancer le step. Si le message n'arrive toujours pas, verifier que
`svc-commandes-activations` est sain : c'est lui qui publie vers le DLQ.

### `-Step Decoupling` laisse un service arrete

Le step restaure `svc-lignes-services` et `svc-catalogue-offres` dans son bloc
`finally`, mais en cas d'interruption au clavier :

```powershell
docker compose -p cantelcox-phase2full up -d --wait svc-lignes-services svc-catalogue-offres
```

### `cantelcox-test:phase2` manquante

Elle est desormais construite automatiquement au premier step qui en a besoin.
Pour la construire a l'avance :

```powershell
docker build -f tests/Dockerfile -t cantelcox-test:phase2 .
```

### La trace Jaeger ne montre qu'un seul span

Verifier que le client envoie bien un en-tete `TraceId` ou `traceparent`, et que
`OTEL_SDK_DISABLED=false`. Sans en-tete, chaque requete ouvre sa propre trace et
la correlation avec les evenements se perd.
