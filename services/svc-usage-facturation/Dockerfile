FROM python:3.12-slim AS builder

WORKDIR /build
COPY services/svc-usage-facturation/requirements.txt /build/requirements.txt
RUN pip install --prefix=/install --no-cache-dir -r /build/requirements.txt

FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /install /usr/local
COPY services/shared /app/services/shared
COPY services/svc-usage-facturation/app /app/app

EXPOSE 5000
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --timeout ${GUNICORN_TIMEOUT:-30} app.main:app"]
