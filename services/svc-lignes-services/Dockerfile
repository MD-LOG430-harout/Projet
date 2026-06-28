FROM python:3.12-slim

WORKDIR /app
COPY services/shared /app/services/shared
COPY services/svc-lignes-services/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/svc-lignes-services/app /app/app

ENV PYTHONPATH=/app
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app.main:app"]
