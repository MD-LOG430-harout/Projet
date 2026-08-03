# Mesures & gains — comparatif synchrone ↔ événementiel

Support de l'étape « Mesures & gains » de l'Annexe D. Toutes les valeurs ont été
mesurées le **2026-08-03** sur la pile complète (`docker compose -p cantelcox-phase2full`,
18 conteneurs). Preuves brutes : [docs/evidence/phase2/perf/2026-08-03-sync-vs-event-driven.json](../evidence/phase2/perf/2026-08-03-sync-vs-event-driven.json).

## Le comparatif honnête

CanTelcoX ne fait pas tourner les deux architectures côte à côte : le code Phase 1
a été remplacé. Comparer des chiffres de Phase 1 archivés à des chiffres de Phase 2
mesurés aujourd'hui, sur une autre machine, n'aurait aucune valeur.

Le comparatif présenté est donc mesuré **dans la pile actuelle**, en opposant deux
dépendances de la *même* requête `POST /v1/orders` :

- `svc-catalogue-offres` est appelé **synchroniquement** pour valider l'offre ;
- `svc-lignes-services` est joint **par événements** pour activer la ligne.

Couper l'une puis l'autre isole exactement ce que le style événementiel change.

## Résultats

| Critère | Dépendance synchrone en panne | Dépendance événementielle en panne |
|---|---|---|
| Service arrêté | `svc-catalogue-offres` | `svc-lignes-services` |
| Codes de réponse | **5 × HTTP 500** | **5 × HTTP 202** |
| Latence observée | 2 577 – 3 884 ms (timeouts) | P95 **116 ms** (inchangée) |
| Commandes acceptées | 0 / 5 | 5 / 5 |
| Après remise en service | rien à rattraper : les requêtes sont perdues | les 5 sagas convergent seules, **0 saga EN_COURS résiduelle** |

Le gain n'est pas la latence brute, c'est le **découplage temporel** : une panne en
aval ne se propage plus au client. Ce qui reste synchrone reste fragile — la
démonstration le montre dans les deux sens, ce qui est le point défendable.

## Latences de la pile complète (20 commandes consécutives)

| Mesure | Valeur | Cible de l'énoncé | Verdict |
|---|---|---|---|
| Acceptation `POST /v1/orders` P50 | 78,7 ms | — | — |
| Acceptation P95 | **115,9 ms** | < 250 ms | ✅ atteinte |
| Convergence de saga P50 | 966,7 ms | — | — |
| Convergence de saga P95 | **1 519,4 ms** | — | — |
| États terminaux | 20 / 20 `CONFIRMEE` | — | ✅ |

Les deux latences mesurent des choses différentes et c'est le cœur du propos :
le `202` est une **acceptation** (116 ms), la convergence de la saga est un
**achèvement** (1,5 s). En synchrone, le client aurait attendu les deux.

## Limites à assumer à l'oral

- **Débit non mesuré ici.** La campagne Locust n'a pas été rejouée sur ce poste ;
  la cible de 1 000 ops/s n'est pas démontrée par ces chiffres.
- **Métriques sous-comptées.** Chaque service tourne avec 2 workers gunicorn ayant
  chacun son registre Prometheus ; un scrape ne voit qu'un worker. Les compteurs
  d'événements sont donc un plancher, pas un total exact.
- **Un test d'intégration instable.**
  `test_increment0_foundations.py::test_outbox_relay_ack_failure_retry_and_two_poller_exclusion`
  échoue par intermittence quand les relais Outbox des services en marche réclament
  la ligne de test avant le relai instancié par le test. Il passe systématiquement
  en isolation. Suite complète du jour : **46 passed, 9 skipped, 0 failed**.
- **free5GC réel non validé** : la démo utilise le HLR simulé, conformément à
  [demo-10-minutes.md](demo-10-minutes.md).

## Protocole de reproduction

Les deux scénarios sont automatisés :

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Decoupling
```

Ce step enchaîne les trois mesures ci-dessus et remet la pile dans son état nominal.
Il dure environ deux minutes : à présenter uniquement si le temps le permet,
sinon montrer ce tableau.

Les scripts de mesure sont versionnés :
[tests/load/measure_saga_latency.py](../../tests/load/measure_saga_latency.py) et
[tests/load/measure_sync_dependency.py](../../tests/load/measure_sync_dependency.py).
