# PowerPoint outline - five slides

Slides 1 to 4 below cover the original 10-minute run. Slide 5 was added for the
15-minute Annexe D flow ([demo-15-minutes.md](demo-15-minutes.md)); it carries
the "Mesures & gains" step, which the four-slide deck did not cover.

## Slide 1 - From Phase 1 to Phase 2

Title: From Phase 1 to Phase 2

Bullets:

- synchronous REST became event-driven
- Kafka + Outbox + saga
- six existing services preserved

Recommended diagram or screenshot:

Use the Phase 2 architecture diagram showing API Gateway, six services, MySQL,
Kafka, PortabilityHub, Prometheus/Grafana, and Jaeger.

Speaker notes, max 45 seconds:

Phase 1 mostly coordinated the services through synchronous REST. Phase 2 keeps
the existing use cases and services, but changes the collaboration style: public
requests are accepted quickly, local state and Outbox events are committed in
MySQL, and Kafka carries the saga facts asynchronously.

## Slide 2 - Nominal saga

Title: Nominal saga

Bullets:

- `CommandePassee -> PaiementAutorise`
- `PaiementAutorise -> LigneActivee`
- `LigneActivee -> CommandeConfirmee`

Recommended diagram or screenshot:

Show the sequence diagram for the nominal order saga, or a terminal command
screenshot showing `HTTP 202`, `Location`, `EN_COURS`, and final `CONFIRMEE`.

Speaker notes, max 45 seconds:

The order endpoint returns `202 Accepted`, not completion. The order service
writes the order, saga state, and `CommandePassee` in one local transaction.
After that, each service consumes and produces facts through Kafka until the
order reaches `CONFIRMEE`.

## Slide 3 - Compensation and portability

Title: Compensation and portability

Bullets:

- `ActivationEchouee -> CommandeAnnulee`
- `CommandeAnnulee -> PaiementRembourse`
- PortabilityHub REST initiation plus callback

Recommended diagram or screenshot:

Show the compensation sequence diagram or a PortabilityHub test output screenshot
with `port_completed` and `rejected` scenarios.

Speaker notes, max 45 seconds:

Compensation is modeled as business facts, not reverse database transactions.
For portability, initiation is synchronous REST to the supplied Hub, then HTTP
callbacks are mapped by the ACL: `port_completed` becomes `NumeroPorte`, while
`rejected` and `cancelled` become `PortabiliteEchouee`.

## Slide 4 - Evidence and limits

Title: Evidence and limits

Bullets:

- 46 passed, 9 skipped, 0 failed (suite rejouee le 2026-08-03)
- acceptation P95 116 ms; convergence de saga P95 1,5 s
- debit non rejoue sur ce poste; free5GC reel non valide

Recommended diagram or screenshot:

Show the evidence folder, the performance summary, or a screenshot of Grafana
Golden Signals plus the final test result.

Speaker notes, max 45 seconds:

La suite rejouee sur la pile complete donne 46 passed, 9 skipped, 0 failed.
L'acceptation de commande est a 116 ms P95, sous la cible de 250 ms, et la saga
converge en 1,5 s P95 sur 20 commandes toutes CONFIRMEE. Le lag Kafka et les
lignes Outbox en attente retombent a zero apres drainage. Les limites honnetes :
le debit n'a pas ete rejoue sur ce poste donc la cible de 1000 ops/s n'est pas
demontree, les compteurs Prometheus sous-comptent a cause des deux workers
gunicorn, un test d'integration Outbox est instable quand les relais tournent, et
le succes free5GC reel n'est pas valide.


## Slide 5 - Mesures & gains

Title: Mesures & gains - synchrone vs evenementiel

Bullets:

- dependance synchrone coupee : 5 x HTTP 500 en 2,6-3,9 s
- dependance evenementielle coupee : 5 x HTTP 202, P95 116 ms, convergence auto
- acceptation P95 116 ms (cible < 250 ms), convergence de saga P95 1,5 s

Recommended diagram or screenshot:

Le tableau comparatif de `docs/demo/mesures-et-gains.md`, ou une capture du
dashboard Grafana `CanTelcoX Event-Driven` montrant le lag consommateur et
l'arriere Outbox.

Speaker notes, max 45 seconds:

Le gain n'est pas la latence brute, c'est le decouplage temporel. En coupant
tour a tour les deux dependances de la meme requete POST /v1/orders, on isole
exactement ce que le style evenementiel change : la dependance appelee
synchroniquement propage sa panne au client, la dependance evenementielle non.
Les limites sont assumees : debit non rejoue sur ce poste, compteurs Prometheus
sous-comptes a cause des deux workers gunicorn, un test d'integration Outbox
instable, et free5GC reel non valide.
