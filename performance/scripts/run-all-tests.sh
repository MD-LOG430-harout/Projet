#!/usr/bin/env bash
set -euo pipefail
mkdir -p performance/results/raw
runner=(docker run --rm --network "${COMPOSE_NETWORK:-projet_default}" -v "$(pwd)/performance:/performance" -w /performance grafana/k6:0.54.0 run)
"${runner[@]}" --summary-export results/phase2-acceptance-summary.json k6/phase2-acceptance.js | tee performance/results/raw/phase2-acceptance.txt
"${runner[@]}" --summary-export results/phase2-saga-summary.json k6/phase2-saga-convergence.js | tee performance/results/raw/phase2-saga.txt
echo 'Compensation is deliberately separate: restart svc-lignes-services with HLR_FORCE_FAILURE=true first.'
