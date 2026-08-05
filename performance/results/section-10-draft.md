# 10. Exigences de qualité — gains mesurés

## 10.1 Cibles NFR et résultats

Les mesures du 5 août 2026 utilisent la pile Docker complète et `POST /v1/orders`. La latence REST s'arrête au 202; la convergence commence après ce 202. Les résultats finaux sont une exécution par palier, et non une médiane de trois.

| Indicateur | Cible | Mesuré final | Verdict |
|---|---:|---:|---|
| Latence REST P95 | ≤ 250 ms | 414,77 ms à 20/s; 614,98 ms à 50/s | Écart — non atteint |
| Latence REST P99 | surveillance | 527,02 ms à 20/s; 783,45 ms à 50/s | Observé |
| Débit durable | ≥ 1 000 ops/s | maximum démontré ≥99 % : 48,01 202/s pour 50/s offertes (15 s) | Écart majeur |
| Succès au seuil durable | ≥ 99 % | 100 % (751/751) à 50/s | Atteint sur ce run court |
| Saga nominale P95 | ≤ 3 s | 2,23 s, 20/20 terminales (final) | Atteint |
| Compensation P95 | ≤ 5 s | 1,63 s, 20/20 cohérentes | Atteint |
| Disponibilité | 99 % | non mesurée sur une durée suffisante | Non démontrée |

## 10.2 Avant/après et campagnes de charge

| Campagne | 202 | Débit 202 | P95 | Erreurs/abandons | Conclusion |
|---|---:|---:|---:|---:|---|
| baseline 20/s | 201/201 | 19,12/s | 482,39 ms | 0/0 | succès, latence échouée |
| final 20/s | 301/301 | 19,15/s | 414,77 ms | 0/0 | gain P95 de 14,0 %, cible échouée |
| final 50/s après MySQL 500 | 751/751 | 48,01/s | 614,98 ms | 0/0 | seuil de succès démontré |
| final 200/s | 1 398/1 425 | 77,00/s | 8,92 s | 27 HTTP 500; 580 abandons | non soutenable |
| final progressif 50→1200→50 | 1 053/8 588 | 27,00/s agrégé | 13,67 s | 6 088×500, 1×502, 1 446×504, 6 408 abandons | 1 000/1 200 non atteints |

Le résultat progressif ne doit pas être lu comme une mesure par palier : le script rampe entre les cibles et son export k6 est agrégé. Même avec 3 000 VU préalloués, les réponses longues saturent le générateur à partir des hauts niveaux. Cela est une conséquence mesurée de la saturation serveur, mais empêche de donner une valeur propre par étape. Aucun débit offert n'est présenté comme débit accepté.

Après le test 200/s, l'Outbox est revenue à zéro en moins de 30 s et seules 3 nouvelles sagas restaient en cours au contrôle. Après le stress, l'Outbox est aussi revenue à zéro en 30 s, avec 3 sagas de la fenêtre encore en cours. Des états anciens issus des essais de saturation subsistent : le critère global zéro orphelin n'est donc pas satisfait.

## 10.3 Causes et gains architecturaux

Le 17,54 % initial provenait principalement de 2 565 erreurs 500 d'authentification Gateway, 457 timeouts 504, resets/EOF et 558 itérations abandonnées. Les mesures de segment montrent que l'introspection (P95 383 ms), la lecture client (315 ms) et le service commandes/MySQL sous charge (1 941 ms) dominaient le P95.

Les changements conservés sont : capacité NGINX 8 192 connexions, réutilisation upstream, cache borné des challenges déjà vérifiés, audit d'acceptation retiré du chemin synchrone mais conservé via Kafka, isolation MySQL `READ COMMITTED`, concurrence Gunicorn 4×16, trois réplicas commandes et plafond MySQL 500. Le bénéfice le plus net est la disparition des erreurs à 50/s après correction MySQL; le P95 reste toutefois supérieur à la cible.

La Phase 1 annonce 500 ms, 600 ops/s et 95 %, mais aucun résultat brut Phase 1 n'est présent. Ces nombres restent des cibles documentaires et ne sont pas présentés comme un avant remesuré. L'événementiel démontre une convergence nominale finale de 2,23 s et une compensation réelle de 1,63 s, pas un débit durable de 1 000/s.

## 10.4 Résilience, idempotence et observabilité

La compensation HLR finale a produit 20 annulations, 20 remboursements distincts, 20 libérations de ligne et les événements d'audit `ActivationEchouee`, `CommandeAnnulee`, `PaiementRembourse`; aucun effet double n'a été observé dans cet échantillon. Le premier essai contaminé par l'état Gateway est conservé dans `final-compensation-hlr.json`; le run valide est `final-compensation-hlr-retry.json`.

Prometheus, Grafana, Jaeger et l'OTel Collector sont restés actifs. Les exports bruts, le lag Kafka et l'Outbox ont été inspectés. En revanche, les captures Grafana/Jaeger, la campagne contrôlée stop/reprise consommateur et le rejeu exact d'un événement dupliqué n'ont pas été recollectés : ces critères restent non cochés.

## 10.5 Critères d'acceptation

- [ ] P95 REST ≤ 250 ms — meilleur final 414,77 ms à 20/s.
- [ ] Débit durable ≥ 1 000 ops/s — non atteint.
- [x] Succès ≥99 % au seuil durable mesuré — 100 % à 50/s sur 15 s.
- [x] Saga nominale P95 ≤3 s — 2,23 s (20/20).
- [x] Compensation P95 ≤5 s — 1,63 s (20/20).
- [ ] Zéro saga orpheline après toutes les saturations — non atteint.
- [ ] Gains avant/après Phase 1 démontrés — résultats Phase 1 bruts absents.
- [ ] Captures tracing, lag et Golden Signals complètes — non recollectées.
