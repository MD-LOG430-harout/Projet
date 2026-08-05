# Journal d'optimisation

| Iteration | Hypothesis | Files changed | Before | After | Decision |
| --------- | ---------- | ------------- | ------ | ----- | -------- |
| 0 | Le résultat initial manque de catégories d'échec et de compteurs d'arrivée | `performance/k6/lib.js`, scripts k6 | 17,54 % agrégé; erreurs non classées; 558 abandons | compteurs started/completed/statuts/timeouts/resets et échantillons bornés | Conservé; correction méthodologique |
| 1 | Le plafond NGINX provoque resets et refus | `infra/nginx/nginx.conf` | 689/3 001 202 à 200/s; 589 échecs connexion | les resets client disparaissent, mais 1 767 réponses 504 exposent la file applicative | Conservé `worker_connections=8192`; keepalive à réévaluer |
| 2 | La concurrence Gunicorn est insuffisante | `.env.example` (`.env` local) | 275 202 au test court 200/s | 559 202; P95 toujours >11 s | Conservé avec surveillance MySQL |
| 3 | `REPEATABLE READ` accentue les verrous des relays concurrents | `services/shared/mysql.py` | 2 235 attentes de verrous; max 456 ms | 609 202 après drainage; amélioration insuffisante seule | Conservé pour `SKIP LOCKED` |
| 4 | Introspection répétée et audit nominal synchrone chargent le chemin 202 | identité `routes.py`/`main.py`, `create_order.py` | 609 202 au court test 200/s | 777 202; taux accepté 30,56/s | Conservé; cache uniquement après vérification DB et borné à 10 000 |
| 5 | Une instance commandes est le principal goulot | déploiement : 3 réplicas commandes | 777 202 | 1 815 202 (88,10 %), 79,03/s acceptées | Conservé; gain net, cible encore échouée |
| 6 | Le scale-out dépasse le plafond MySQL de 151 | `docker-compose.yml`, `.env.example` | erreurs 1040; 174 réponses 502 à 50/s | 751/751 202, zéro erreur à 50/s; P95 614,98 ms | Conservé; plafond effectif 500 |
| 7 | Un seul échec d'une adresse Docker marque le nom upstream entier indisponible | `infra/nginx/nginx.conf` | `no live upstreams`, 17×502 lors du premier essai compensation | configuration validée avec `max_fails=0`; Docker healthchecks et retries restent actifs | Conservé; évite l'état de panne NGINX persistant |

Les fichiers `optimization-*.json` et `final-*.json` sont les exports k6 bruts. Une exécution contaminée par un backlog (`optimization-3-read-committed-rate-200.json`) est conservée mais exclue des comparaisons; sa variante drainée est explicitement nommée.
