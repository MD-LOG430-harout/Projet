#!/usr/bin/env bash
set -euo pipefail
out="${1:-performance/results/failure-recovery.csv}"
duration="${DURATION_SECONDS:-120}"
interval="${INTERVAL_SECONDS:-2}"
mkdir -p "$(dirname "$out")"
echo 'timestamp,consumer_state,kafka_lag,outbox_pending,active_sagas,completed_sagas,errors' > "$out"
end=$((SECONDS + duration))
while (( SECONDS < end )); do
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  state="$(docker compose ps --status running --services | grep -c '^svc-lignes-services$' || true)"
  lag="$(docker compose exec -T kafka /opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server kafka:9092 --describe --group svc-lignes-services 2>/dev/null | awk 'NR>2 && $6 ~ /^[0-9]+$/ {s+=$6} END {print s+0}')"
  row="$(docker compose exec -T mysql mysql -N -ucantelcox -p"${MYSQL_PASSWORD:-cantelcox_dev}" -e "SELECT (SELECT COUNT(*) FROM commandes_activations.outbox_events WHERE published_at IS NULL)+(SELECT COUNT(*) FROM usage_facturation.outbox_events WHERE published_at IS NULL)+(SELECT COUNT(*) FROM lignes_services.outbox_events WHERE published_at IS NULL),(SELECT COUNT(*) FROM commandes_activations.saga_state WHERE status='EN_COURS'),(SELECT COUNT(*) FROM commandes_activations.saga_state WHERE status IN ('CONFIRMEE','ANNULEE'));" 2>/dev/null | tr '\t' ',')"
  errors="$(curl -fsS 'http://localhost:9090/api/v1/query?query=sum(increase(cantelcox_events_handler_failures_total%5B2m%5D))' 2>/dev/null | sed -n 's/.*"value":\[[^,]*,"\([^"]*\)"\].*/\1/p')"
  echo "$ts,$state,$lag,$row,${errors:-NA}" >> "$out"
  sleep "$interval"
done
echo "Wrote $out"
