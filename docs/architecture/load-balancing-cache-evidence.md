# Load Balancing et Cache - Evidence Phase 1

Ce document complete la section 5.3/5.4 du gabarit LOG430. Il reste limite au perimetre officiel: UC-02 pour le setup MFA, UC-03 activation et UC-05 catalogue/commande dans Locust.

## Load Balancing

NGINX est place devant les services et utilise des upstreams `least_conn` avec resolution DNS Docker. Les appels officiels passent toujours par `http://localhost:8080`.

### Procedure N = 1..4

```powershell
docker compose up -d --scale svc-catalogue-offres=1 --scale svc-commandes-activations=1 --scale svc-lignes-services=1
docker compose restart api-gateway
docker compose --profile load-test run --no-deps --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-n1.html

docker compose up -d --scale svc-catalogue-offres=2 --scale svc-commandes-activations=2 --scale svc-lignes-services=2
docker compose restart api-gateway
docker compose --profile load-test run --no-deps --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-n2.html

docker compose up -d --scale svc-catalogue-offres=3 --scale svc-commandes-activations=3 --scale svc-lignes-services=3
docker compose restart api-gateway
docker compose --profile load-test run --no-deps --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-n3.html

docker compose up -d --scale svc-catalogue-offres=4 --scale svc-commandes-activations=4 --scale svc-lignes-services=4
docker compose restart api-gateway
docker compose --profile load-test run --no-deps --rm locust -f /mnt/locust/locustfile.py --host=http://api-gateway --headless -u 50 -r 5 -t 2m --html /mnt/evidence/locust-n4.html
```

### Tableau a remplir

| N instances | RPS | P95 (ms) | Erreurs | Saturation observee |
|---:|---:|---:|---:|---|
| 1 | A completer | A completer | A completer | A completer |
| 2 | A completer | A completer | A completer | A completer |
| 3 | A completer | A completer | A completer | A completer |
| 4 | A completer | A completer | A completer | A completer |

### Tolerance aux pannes

1. Demarrer avec N=2 ou plus.
2. Lancer Locust pendant 2 minutes.
3. Pendant le test, arreter un conteneur replique:

```powershell
docker ps --filter "name=svc-commandes-activations" --format "{{.Names}}"
docker stop <nom-du-conteneur>
```

4. Capturer le rapport Locust et calculer:

```text
Disponibilite observee = requetes reussies / requetes totales
```

## Cache Redis Catalogue

Le cache est volontairement limite au catalogue, car UC-04 usage est hors perimetre.

| Endpoint | Cle Redis | TTL | Strategie |
|---|---|---:|---|
| `GET /v1/offers` | `catalogue:offers:active` | `OFFER_CACHE_TTL_SECONDS`, defaut 60s | TTL |
| `GET /v1/offers/{offerId}` | `catalogue:offer:{offerId}` | `OFFER_CACHE_TTL_SECONDS`, defaut 60s | TTL |

La reponse contient `X-Cache: MISS` au premier appel puis `X-Cache: HIT` si le second appel arrive avant expiration.

### Verification rapide

```powershell
$headers = @{ Authorization = "Bearer <accessToken>"; TraceId = "cache-demo" }
Invoke-WebRequest -Uri "http://localhost:8080/v1/offers" -Headers $headers | Select-Object -ExpandProperty Headers
Invoke-WebRequest -Uri "http://localhost:8080/v1/offers" -Headers $headers | Select-Object -ExpandProperty Headers
```

Pour le rapport, joindre une capture des deux headers et comparer la latence `GET UC-05 consult offers` dans Locust avant/apres cache.

## Limites

- L'invalidation est TTL-only en Phase 1, car le catalogue est seed/read-only.
- Si une API d'administration du catalogue est ajoutee plus tard, elle devra supprimer `catalogue:offers:active` et `catalogue:offer:{offerId}`.
- La disponibilite 95% sous panne doit etre mesuree localement; elle ne doit pas etre declaree atteinte sans rapport Locust.
