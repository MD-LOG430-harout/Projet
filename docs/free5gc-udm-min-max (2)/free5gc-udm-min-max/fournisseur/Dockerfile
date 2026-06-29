# Conteneur "fournisseur" : un client minimal qui interroge l'UDM 3GPP
# via le reseau Docker (appel SBI Nudm_SDM en HTTP/2).
FROM python:3.12-slim

WORKDIR /app

# httpx supporte HTTP/2 (requis par les interfaces SBI 3GPP) ;
# requests ne fait que du HTTP/1.1.
RUN pip install --no-cache-dir "httpx[http2]==0.27.*"

COPY query_udm.py .

CMD ["python", "query_udm.py"]
