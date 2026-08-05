#!/usr/bin/env bash
set -euo pipefail
echo "This script intentionally does not delete shared volumes or business data."
docker compose exec -T redis redis-cli FLUSHDB
echo "Redis test cache cleared. For a destructive full reset, explicitly run: docker compose down -v"
