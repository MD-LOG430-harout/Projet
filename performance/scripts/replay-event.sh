#!/usr/bin/env bash
set -euo pipefail
event_file="${1:?usage: replay-event.sh EVENT_JSON_FILE TOPIC}"
topic="${2:?usage: replay-event.sh EVENT_JSON_FILE TOPIC}"
test -s "$event_file"
python -m json.tool "$event_file" >/dev/null
cat "$event_file" | docker compose exec -T kafka /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic "$topic"
echo "Replayed the exact JSON (including its existing eventId) to $topic"
