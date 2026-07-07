#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-deploy}"
APP_DIR="${APP_DIR:-$(pwd)}"
DEPLOY_REF="${DEPLOY_REF:-main}"
STATE_DIR="${APP_DIR}/.deploy"
PREVIOUS_REV_FILE="${STATE_DIR}/previous_revision"
CURRENT_REV_FILE="${STATE_DIR}/current_revision"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-300}"

cd "$APP_DIR"
mkdir -p "$STATE_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 is required" >&2
    exit 127
  fi
}

ensure_env_file() {
  if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example. Review local secrets before production use."
  fi
}

current_revision() {
  git rev-parse --verify HEAD
}

wait_for_health() {
  if [ -x scripts/wait-compose-health.sh ]; then
    scripts/wait-compose-health.sh "$HEALTH_TIMEOUT_SECONDS"
  else
    bash scripts/wait-compose-health.sh "$HEALTH_TIMEOUT_SECONDS"
  fi
}

deploy() {
  require_command docker
  require_command git
  ensure_env_file

  CURRENT_REVISION="$(current_revision)"
  echo "$CURRENT_REVISION" > "$PREVIOUS_REV_FILE"

  git fetch --all --prune
  git checkout "$DEPLOY_REF"

  NEW_REVISION="$(current_revision)"
  echo "$NEW_REVISION" > "$CURRENT_REV_FILE"

  docker compose config >/dev/null
  docker compose build
  docker compose up -d
  wait_for_health

  echo "Deployment completed at revision $NEW_REVISION."
}

rollback() {
  require_command docker
  require_command git
  ensure_env_file

  if [ ! -f "$PREVIOUS_REV_FILE" ]; then
    echo "No previous revision recorded in $PREVIOUS_REV_FILE." >&2
    exit 1
  fi

  TARGET_REVISION="$(cat "$PREVIOUS_REV_FILE")"
  git checkout "$TARGET_REVISION"
  echo "$TARGET_REVISION" > "$CURRENT_REV_FILE"

  docker compose config >/dev/null
  docker compose build
  docker compose up -d
  wait_for_health

  echo "Rollback completed at revision $TARGET_REVISION."
}

case "$ACTION" in
  deploy)
    deploy
    ;;
  rollback)
    rollback
    ;;
  status)
    docker compose ps
    ;;
  logs)
    docker compose logs --tail="${LOG_TAIL:-200}"
    ;;
  *)
    echo "Usage: $0 [deploy|rollback|status|logs]" >&2
    exit 2
    ;;
esac
