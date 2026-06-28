FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY services/shared /app/services/shared
COPY services/svc-clients-identite/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/svc-clients-identite/app /app/app

EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app.main:app"]
