# Analyse des causes racines — Phase 2

Date des essais : 5 août 2026. Environnement : pile Docker Compose complète sur Docker Desktop, sécurité, MySQL, Kafka, Outbox, audit, métriques et tracing actifs. L'API réellement implémentée est `POST /v1/orders` (et non `/v1/commandes`).

## Validité de la méthode initiale

Le choix `ramping-arrival-rate`, les clés d'idempotence uniques, les données valides, le `setup()` hors mesure et l'exclusion du polling de saga de la latence d'acceptation étaient corrects. Le probe initial ne permettait toutefois pas d'inférer une capacité soutenable : 558 itérations avaient été abandonnées, les statuts et erreurs réseau n'étaient pas ventilés, les échantillons d'erreur n'étaient pas conservés et les étapes de 5 s étaient trop courtes. Les résultats originaux sont conservés sous `baseline-phase2-*.json`; les scripts corrigés comptent les requêtes démarrées/terminées, chaque statut, timeouts, erreurs de connexion et échantillons bornés.

## Classification du probe original

Les journaux Gateway de la fenêtre originale contiennent 3 665 réponses; k6 a aussi subi de nombreuses fins de connexion sans réponse et 558 itérations abandonnées.

| Catégorie | Compte connu | Pourcentage des réponses Gateway | Exemple | Origine | Cause probable |
|---|---:|---:|---|---|---|
| 202 | 643 | 17,54 % | `Accepted` | commandes | capacité utile |
| 400 | 0 | 0 % | — | — | données valides |
| 401/403 | 0 | 0 % | — | — | jeton valide |
| 409 | 0 | 0 % | — | — | clés uniques |
| 429 | 0 | 0 % | — | — | aucun rate limiter |
| 500 | 2 565 | 69,99 % | `auth request unexpected status` | Gateway/auth | identité saturée et connexions Gateway |
| 502/503 | 0 observé | 0 % | — | — | — |
| 504 | 457 | 12,47 % | upstream timeout | Gateway/commandes | file d'attente du service commandes |
| timeout client | non isolé initialement | — | EOF/timeout | k6/Gateway | instrumentation initiale insuffisante |
| refus/reset | inclus dans les échecs sans réponse | — | reset/EOF | NGINX | plafond de 512 connexions worker |
| itération k6 abandonnée | 558 | hors réponses | insufficient VUs | k6 | latence serveur élevée, VU épuisés |

Le test corrigé à 200/s avant optimisation a rendu 689 réponses 202 (22,95 %), 1 723 réponses 500 (57,41 %) et 589 échecs de connexion (19,63 %), sans abandon. Cela confirme que le serveur, pas les données de test, était dominant.

## Profil du chemin critique

La réponse 202 attend bien seulement : authentification Gateway, lecture client, lecture offre, recherche d'idempotence, transaction locale `orders + saga_state + outbox_events`, commit et sérialisation. Elle n'attend ni Kafka, ni paiement, ni HLR, ni convergence de saga. En mode audit `summary`, l'acceptation n'attend plus un acquittement d'audit; `CommandePassee` reste auditée par le consommateur Kafka.

Mesures Prometheus lors du test contrôlé à 200/s :

| Segment | P50 | P95 | P99 |
|---|---:|---:|---:|
| introspection identité | 153 ms | 383 ms | 500 ms |
| lecture client | 51 ms | 315 ms | n/d |
| service commandes | 979 ms | 1 941 ms | 2 340 ms |
| audit synchrone (avant retrait du chemin nominal) | 83 ms | 202 ms | n/d |

La cause dominante du P95 initial de 482,39 ms est donc l'addition des validations REST/authentification et de la transaction MySQL sous contention. Le catalogue disposait déjà d'un cache Redis; les clients HTTP utilisent une `Session` et le trafic interne ne repasse pas par le Gateway externe.

## Saturations confirmées

- NGINX : `worker_connections=512` causait resets/EOF; porté à 8 192.
- Identité : introspection répétée; un cache borné de challenges déjà vérifiés supprime les lectures MySQL répétitives sans accepter un jeton jamais validé.
- Commandes : une instance plafonnait; trois réplicas améliorent nettement l'acceptation à 200/s.
- MySQL : après la mise à l'échelle, traces explicites `OperationalError (1040, Too many connections)` et maximum 151; plafond porté à 500. Aucun OOM ni redémarrage des trois instances.
- Verrous : 2 235 attentes InnoDB et attente maximale de 456 ms; isolation passée à `READ COMMITTED`. Le relay Outbox publie hors transaction SQL; son plan utilise `idx_outbox_pending`, avec un filesort restant.
- Sous stress final, la latence de 10–15 s épuise même 3 000 VU et provoque 500/504. La pile est principalement contention/connexion/downstream-latency-bound, pas démontrée CPU- ou mémoire-bound.

## Résultat final et limites

À 50/s après correction MySQL : 751/751 réponses 202, zéro erreur et zéro abandon, mais P95 614,98 ms. À 200/s : 1 398/1 425 réponses 202, 27 réponses 500, 580 abandons, débit accepté 77,00/s et P95 8,92 s. La campagne progressive corrigée a produit 1 053 réponses 202, 6 088 réponses 500, 1 réponse 502, 1 446 réponses 504 et 6 408 abandons; débit accepté agrégé 27,00/s et P95 13,67 s.

Le maximum démontré avec ≥99 % de succès est donc 50 commandes/s offertes (48,01/s acceptées sur une exécution de 15 s), mais il ne respecte pas la cible de latence. Ce test court ne suffit pas à certifier un SLO de disponibilité à long terme. La cible 1 000/s n'est pas atteinte durablement. Des sagas anciennes issues des campagnes de saturation sont restées `EN_COURS`; elles ne sont pas masquées et invalident une affirmation globale « zéro orphelin » après tous les stress.

La campagne nominale finale a confirmé 20/20 sagas avec un P95 de 2,23 s. La campagne HLR déterministe finale a compensé 20/20 sagas, P95 1,63 s : 20 commandes `ANNULEE`, 20 paiements `REMBOURSE` avec 20 `refund_id` distincts, 20 lignes `RELEASED` et 60 événements d'audit correspondants.

CPU, mémoire, captures Grafana/Jaeger, test d'arrêt/reprise consommateur et rejeu d'un doublon n'ont pas été recollectés dans cette passe. Ils restent explicitement non démontrés plutôt que fabriqués.
