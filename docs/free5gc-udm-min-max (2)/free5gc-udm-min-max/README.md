# LOG430 — Mini-cœur 5G free5GC (UDM/UDR + WebConsole)

Cœur 5G **free5GC** réduit aux fonctions de **gestion des données d'abonnés** : MongoDB, NRF, UDR, UDM et WebConsole. Sert de réseau simulé (HLR/HSS) pour le projet CanTelcoX : provisioning des abonnés (WebConsole) et stockage de l'usage (MongoDB).

> Aucune image à construire : `free5gc/*:v4.1.0` et `mongo:7` sont publiques sur Docker Hub. Tout est inclus dans ce dépôt (configs + certificats de test).

## Prérequis

- Docker Desktop (avec Docker Compose)
- macOS : le port 5000 est souvent pris par **AirPlay Receiver** → la WebConsole est publiée sur **5050** (rien à faire).

## Démarrage

```bash
git clone <URL-de-ce-depot>
cd free5gc-udm-min
docker compose -f docker-compose.udm-min.yaml up -d db nrf udr udm webui usage-api
docker compose -f docker-compose.udm-min.yaml ps        # tout doit être "Up"
```

## Accès

| Service | Adresse | Notes |
|---|---|---|
| WebConsole (provisioning) | http://localhost:5050 | identifiants `admin` / `free5gc` |
| MongoDB (usage / UDR) | `mongodb://localhost:27017/free5gc` | publié sur l'hôte |
| UDM (SBI Nudm_SDM) | interne au réseau Docker | testé par le conteneur `fournisseur` |
| usage-api (CDR lecture/écriture) | http://localhost:8090 | façade REST devant `cantelcox_usage` ; Swagger sur `/docs` |

PLMN par défaut : **20893** (MCC 208 / MNC 93) → SUPI `imsi-208930000000001`.

## Créer un abonné

Soit dans la WebConsole (*Subscribers → New Subscriber*, garder les valeurs par défaut), soit via la collection Postman `postman/webconsole-provisioning.postman_collection.json` (Login → Create subscriber). **Sans abonné, l'UDM répond 404.**

## Tester l'UDM (optionnel)

```bash
docker compose -f docker-compose.udm-min.yaml up --build fournisseur
```

Le conteneur fait un appel SBI `Nudm_SDM` (HTTP/2) à l'UDM et affiche les données d'abonnement. Voir aussi `postman/nudm-sdm.postman_collection.json`.

## Simuler de l'usage (CDR)

Le service `usage-api` joue le rôle du CHF : il écrit/lit des CDR dans `cantelcox_usage`. Voir la collection `postman/usage-api.postman_collection.json`, ou en `curl` :

```bash
# 50 CDR aléatoires sur 30 jours
curl -X POST "http://localhost:8090/usage/14385551234/simulate?count=50&days=30"
# 1 CDR data de 500 Mo
curl -X POST http://localhost:8090/usage/14385551234 \
     -H 'Content-Type: application/json' -d '{"type":"DATA","quantity":524288000}'
# lecture / agrégat / purge
curl http://localhost:8090/usage/14385551234
curl "http://localhost:8090/usage/14385551234/summary?cycle=2026-06"
curl -X DELETE http://localhost:8090/usage/14385551234
```

## Intégration avec CanTelcoX (BSS)

CanTelcoX s'y branche sans configuration supplémentaire :

- `lines-services` → WebConsole sur `host.docker.internal:5050` (provisioning à l'activation, UC-03) ; vérification via UDM sur `:8000` (UC-03).
- `usage-billing` → **usage-api** sur `host.docker.internal:8090` (lecture de l'usage, UC-04/08) — plus d'accès Mongo direct depuis le BSS.

Démarre d'abord ce cœur, puis `docker compose up -d` dans le projet CanTelcoX.

## Arrêt

```bash
docker compose -f docker-compose.udm-min.yaml down       # conserve les données
docker compose -f docker-compose.udm-min.yaml down -v    # réinitialise MongoDB
```

## Contenu du dépôt

```
docker-compose.udm-min.yaml   # la stack (db, nrf, udr, udm, webui, usage-api, fournisseur)
config/                       # nrfcfg, udrcfg, udmcfg, webuicfg
cert/                         # certificats de test free5GC
fournisseur/                  # conteneur de test UDM (Nudm_SDM)
usage-api/                    # façade REST de l'usage (CDR lecture/écriture)
postman/                      # collections WebConsole + Nudm_SDM + usage-api
docs/                         # intégration free5GC par cas d'utilisation (.md + .pdf + diagrammes)
```

*free5GC est distribué sous licence Apache 2.0. Certificats de test à usage pédagogique uniquement — ne jamais utiliser en production.*
