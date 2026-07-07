#!/usr/bin/env bash
set -euo pipefail

TIMEOUT_SECONDS="${1:-300}"
INTERVAL_SECONDS="${WAIT_INTERVAL_SECONDS:-5}"
DEADLINE=$((SECONDS + TIMEOUT_SECONDS))

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 127
fi

while true; do
  mapfile -t CONTAINERS < <(docker compose ps -q)

  if [ "${#CONTAINERS[@]}" -eq 0 ]; then
    echo "No Compose containers are running yet."
    sleep "$INTERVAL_SECONDS"
  else
    PENDING=0

    for CONTAINER_ID in "${CONTAINERS[@]}"; do
      NAME="$(docker inspect --format '{{.Name}}' "$CONTAINER_ID" | sed 's#^/##')"
      STATE="$(docker inspect --format '{{.State.Status}}' "$CONTAINER_ID")"
      EXIT_CODE="$(docker inspect --format '{{.State.ExitCode}}' "$CONTAINER_ID")"
      HEALTH="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER_ID")"

      if [ "$HEALTH" = "healthy" ]; then
        continue
      fi

      if [ "$HEALTH" = "none" ] && [ "$STATE" = "running" ]; then
        continue
      fi

      if [ "$STATE" = "exited" ] && [ "$EXIT_CODE" = "0" ]; then
        continue
      fi

      echo "Waiting for $NAME: state=$STATE health=$HEALTH exitCode=$EXIT_CODE"
      PENDING=1
    done

    if [ "$PENDING" -eq 0 ]; then
      echo "All Compose containers are healthy, running, or completed successfully."
      docker compose ps
      exit 0
    fi

    sleep "$INTERVAL_SECONDS"
  fi

  if [ "$SECONDS" -ge "$DEADLINE" ]; then
    echo "Timed out after ${TIMEOUT_SECONDS}s waiting for Compose healthchecks." >&2
    docker compose ps >&2 || true
    docker compose logs --tail=120 >&2 || true
    exit 1
  fi
done
