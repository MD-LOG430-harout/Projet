10.5 Load balancing & caching

Résultats de la phase 2 pour le load balancing de la Saga A (Prise de commande) :

Cette section évalue l'effet de la mise à l'échelle horizontale et du load balancing NGINX (least_conn) sur le débit, la latence et les erreurs du parcours événementiel POST /v1/orders, qui déclenche la saga choréographiée CommandePassee -> PaiementAutorise -> LigneActivee -> CommandeConfirmee via Kafka. Contrairement à la phase 1, l'endpoint testé retourne 202 Accepted immédiatement après la transaction locale (commande + état de saga + événement Outbox) ; la cible NFR de latence porte donc sur cette acceptation REST, pas sur la convergence complète de la saga.

Les campagnes ont été exécutées avec Locust via l'API Gateway (scénario CanTelcoXPhase2OrdersUser : GET /v1/offers "UC-05 consult offers" et POST /v1/orders "UC-05 create order"), 210 utilisateurs simulés, montée de 20 utilisateurs/s, avec un temps d'attente de 0,1 à 0,2 s entre les requêtes de chaque utilisateur afin de maintenir le débit dans la fourchette cible de 1000 à 1500 opérations/s. Les tables orders, outbox_events, processed_events et saga_state ont été purgées avant chaque campagne pour éviter qu'un traitement asynchrone résiduel d'une campagne précédente ne fausse les mesures suivantes. L'objectif était de comparer le comportement du système avec 1, 2, 3 et 4 instances de svc-commandes-activations et svc-catalogue-offres.

N instances	RPS agrégé	P95 create order (ms)	Erreurs	Saturation
1	1281.8	36	0	Non observée : P95 < 250 ms, aucun échec
2	1288.5	22	0	Non observée : P95 < 250 ms, aucun échec
3	1283.5	180	0	Non observée : P95 < 250 ms, aucun échec
4	1266.4	33	0	Non observée : P95 < 250 ms, aucun échec

Les cibles NFR de la phase 2 (P95 ≤ 250 ms pour l'acceptation REST, débit ≥ 1000 ops/s) sont atteintes pour N = 1 à N = 4, sans aucun échec sur l'ensemble des campagnes. Le débit reste stable autour de 1266 à 1289 RPS, à l'intérieur de la fourchette visée. La latence P95 de create order varie davantage (22 à 180 ms) que le débit, mais reste dans tous les cas nettement sous la cible de 250 ms ; cette variation reflète surtout le bruit statistique d'un échantillon modeste (1200 à 1400 requêtes de commande par campagne) plutôt qu'une tendance de scalabilité, puisqu'aucune des quatre configurations ne sature réellement svc-commandes-activations à ce niveau de charge -- la capacité réelle du service, mesurée sans plafonnement du débit plus tôt dans la campagne de validation, se situe plutôt autour de 2400 à 2900 RPS agrégés. Le load balancing est donc validé comme mécanisme de répartition et de déploiement multi-instance capable d'absorber la charge cible sans dégradation, mais un gain de scalabilité horizontale mesurable nécessiterait une charge poussée plus près de ce plafond de capacité réel.

Caching

Résultats de la phase 2 pour le cache de catalogue :

Cette section constitue la seconde optimisation après la baseline de la phase 2 : le cache Redis est utilisé pour réduire les lectures répétées sur le catalogue et améliorer la latence de l'endpoint de consultation des offres. Comme en phase 1, le cache est appliqué exclusivement à GET /v1/offres, dans le service svc-catalogue-offres, avec un TTL de 60 secondes. L'objectif reste le même : réduire les lectures répétées vers MySQL et stabiliser la latence sous charge, mais la mesure est faite ici avec le scénario de charge orienté saga (CanTelcoXPhase2OrdersUser), qui combine la consultation d'offres et la création de commande événementielle POST /v1/orders.

Les campagnes ont été exécutées à N = 1 instance de svc-catalogue-offres, 210 utilisateurs simulés, montée de 20 utilisateurs/s, sur 75 secondes, avec les tables orders, outbox_events, processed_events et saga_state purgées avant chaque campagne pour une mesure comparable. Le cache a été désactivé pour la campagne de référence en vidant la variable REDIS_URL du service, ce qui force chaque requête GET /v1/offers à interroger directement MySQL.

Les résultats montrent un gain nettement plus marqué qu'en phase 1 : le P95 de GET /v1/offres passe de 88 ms sans cache à 9 ms avec cache, soit un gain d'environ 89,8 %. Le débit agrégé passe de 1058 à 1280 RPS pour les mêmes paramètres de charge Locust, soit un gain d'environ 21 % -- sans cache, chaque requête attendant une réponse MySQL plus lente, moins d'itérations se complètent par seconde par utilisateur simulé. Ce gain plus marqué qu'en phase 1 s'explique par le volume de charge nettement plus élevé de la phase 2 (environ 1250 req/s contre 329 req/s en phase 1) : à ce débit, l'absence de cache force MySQL à traiter plusieurs centaines de lectures supplémentaires par seconde, ce qui allonge sensiblement la file d'attente et la latence. L'endpoint POST /v1/orders n'est pas affecté par ce cache, puisqu'il ne consulte pas le catalogue en mode acceptation rapide (FAST_ORDER_ACCEPTANCE_ENABLED).

Le scénario UC-04 -- Consultation d'usage n'étant toujours pas implémenté en phase 2, aucun test de cache n'a été exécuté sur l'usage.

Endpoint	P95 sans cache	P95 avec cache	Charge DB	Débit sans cache	Débit avec cache	Gain P95
Catalogue /v1/offers	88 ms	9 ms	Réduite après MISS initial; HIT Redis pendant TTL de 60s	1045.0 RPS	1264.0 RPS	89.8%
Usage	Hors périmètre UC-04	Hors périmètre UC-04	Non mesuré	Non mesuré	Non mesuré	N/A

La capture montre la campagne Locust avec cache activé. Le système traite 103961 requêtes sur 75 secondes, avec 0 échec, un débit agrégé de 1279.8 RPS et un P95 agrégé de 10 ms. Pour GET /v1/offers, le débit atteint 1264.0 RPS avec un P95 de 9 ms.

capture locust avec cache

La capture présente la campagne Locust exécutée avec le cache désactivé pour l'endpoint GET /v1/offers (REDIS_URL vide). Ce scénario sert de référence avant optimisation. Le débit agrégé atteint 1058.0 RPS avec un P95 agrégé de 88 ms et 1 échec transitoire (502) sur 87864 requêtes.

capture locust sans cache
