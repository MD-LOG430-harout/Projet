# Test runner image used by docs/demo/demo-commands.ps1 (tag: cantelcox-test:phase2).
# Build from the repository root:
#   docker build -f tests/Dockerfile -t cantelcox-test:phase2 .
# The repository itself is bind-mounted at run time, so only the dependencies are baked in.
FROM python:3.12-slim

WORKDIR /repo
ENV PYTHONPATH=/repo \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# svc-commandes-activations carries the superset of runtime and test dependencies
# (Flask, PyMySQL, kafka-python, jsonschema, prometheus-client, opentelemetry, pytest, requests).
COPY services/svc-commandes-activations/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENTRYPOINT []
CMD ["pytest", "-q"]
