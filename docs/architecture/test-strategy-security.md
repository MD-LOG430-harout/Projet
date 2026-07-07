# Strategie de tests et securite applicative - Phase 1

Ce document relie l'implementation actuelle aux exigences LOG430 7.1 et 7.2. Il couvre uniquement le perimetre officiel retenu pour la Phase 1:

- UC-01 Inscription et verification d'identite
- UC-02 Authentification et MFA
- UC-03 Activation d'une ligne
- UC-05 Prise de commande
- UC-06 Paiement de facture

UC-04, UC-07 complet et UC-08 sont hors perimetre. Les controles anti-fraude sont donc limites aux controles de risque necessaires aux UC retenus.

## 7.1 Strategie de tests

### Pyramide de tests

| Niveau | Emplacement | Objectif | Exemples couverts |
|---|---|---|---|
| Unit / domaine | `services/*/tests` | Valider les regles metier sans demarrer toute la plateforme | creation client, MFA, activation line state, commandes, paiements, erreurs metier |
| Integration par frontiere d'adaptateur | `tests/integration/` | Valider chaque frontiere port/adaptateur distincte contre une dependance reelle lorsque disponible | persistence MySQL des agregats principaux, passerelle paiement simulee, free5GC live optionnel |
| E2E gateway | `tests/e2e/test_gateway_flow.py` et collection Postman/Newman | Orchestrer le scenario telecom via `http://localhost:8080`; Postman est une preuve E2E, pas un test d'integration | inscription -> MFA -> offre -> commande -> activation -> facture -> paiement -> audit |
| Charge / NFR | `tests/load/locustfile.py` | Mesurer latence, RPS et erreurs sous charge via API Gateway | UC-02 pour MFA/setup, UC-03 et UC-05; UC-04 et UC-08 hors perimetre, UC-06 teste fonctionnellement mais retire du scenario officiel Golden Signals |

### Commandes de validation

Suite officielle de tests service:

```bash
python -m pytest -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Dernier resultat mesure:

```text
50 passed
```

Couverture ciblee sur les couches critiques `application` + `domain` seulement. Les adapters/infrastructure ne sont pas inclus dans la cible unitaire de 80%; ils sont valides par les tests d'adapters, la suite E2E et les preuves Docker/Postman.

```bash
python -m pytest --cov=services/svc-clients-identite/app/application --cov=services/svc-clients-identite/app/domain --cov=services/svc-catalogue-offres/app/application --cov=services/svc-catalogue-offres/app/domain --cov=services/svc-lignes-services/app/application --cov=services/svc-lignes-services/app/domain --cov=services/svc-commandes-activations/app/application --cov=services/svc-commandes-activations/app/domain --cov=services/svc-usage-facturation/app/application --cov=services/svc-usage-facturation/app/domain --cov=services/svc-conformite-audit/app/application --cov=services/svc-conformite-audit/app/domain --cov-report=term-missing --cov-report=html:docs/evidence/coverage/htmlcov -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Dernier resultat mesure:

```text
50 passed
TOTAL 87%
HTML report: docs/evidence/coverage/htmlcov/index.html
```

Test E2E gateway, a lancer apres `docker compose up --build`:

```bash
python -m pytest -p no:cacheprovider tests/e2e/test_gateway_flow.py
```

Le test E2E est saute automatiquement si `http://localhost:8080/health` n'est pas disponible.

Tests d'integration automatises par frontiere d'adaptateur, a lancer apres `docker compose up --build`:

```bash
python -m pytest -p no:cacheprovider tests/integration
```

Dernier resultat mesure:

```text
7 passed, 1 skipped
```

Ces tests couvrent les frontieres par adaptateur, pas les UC un par un:

| Frontiere d'adaptateur | Agregat / ressource | Dependence reelle | Evidence |
|---|---|---|---|
| `MysqlCustomerRepository`, `MysqlMfaRepository` | Client, MFA challenge | MySQL `clients_identite` | create/find/update customer, create/verify MFA |
| `MysqlOfferRepository` | Offre / forfait | MySQL `catalogue_offres` | lecture des offres seed et filtre actif |
| `MysqlLineRepository` | Ligne, MSISDN, SIM/eSIM | MySQL `lignes_services` | create/find, transition ACTIVE/FAILED, unicite MSISDN |
| `MysqlActivationRepository` | Activation, commande | MySQL `commandes_activations` | idempotency-key unique pour activations et commandes |
| `MysqlUsageBillingRepository` | Facture, paiement | MySQL `usage_facturation` | paiement, facture PAID, protection paiement unique par facture |
| `MysqlAuditRepository` | Evenement audit | MySQL `conformite_audit` | append, lecture par TraceId, suppression refusee par trigger |
| `SimulatedPaymentGateway` | Paiement externe | Passerelle simulee locale | paiement accepte et echec simule |
| `Free5gcHlrAdapter` | Provisioning HLR/HSS/UDM | free5GC WebConsole live, optionnel | test saute par defaut; lancer avec `FREE5GC_LIVE_TEST=1` lorsque le simulateur est disponible |

### Regles critiques testees

| Domaine critique | Evidence |
|---|---|
| UC-01 identite | `services/svc-clients-identite/tests/test_registration.py`, validation email, adresse et piece d'identite simulee |
| UC-02 MFA | `services/svc-clients-identite/tests/test_auth_mfa.py`, login, OTP, MFA invalide/expire, lockout |
| UC-03 activation | `services/svc-commandes-activations/tests/test_create_activation.py`, `services/svc-lignes-services/tests/test_activate_line.py` |
| UC-03 free5GC adapter | `services/svc-lignes-services/tests/test_free5gc_hlr_adapter.py` |
| UC-05 commande | `services/svc-commandes-activations/tests/test_create_order.py` |
| UC-06 paiement | `services/svc-usage-facturation/tests/test_invoices_payments.py` |
| Audit append-only | `services/svc-conformite-audit/tests/test_audit_append_only.py`, `tests/integration/test_mysql_repository_boundaries.py`, et preuve DB/TraceId en E2E |
| Catalogue/offres | `services/svc-catalogue-offres/tests/test_get_offer.py` |
| Scenario E2E telecom | `tests/e2e/test_gateway_flow.py` |

### Idempotence et exactly-once

| Exigence | Couverture |
|---|---|
| UC-03 activation idempotente | Meme `Idempotency-Key` + meme payload retourne la meme activation; payload different retourne conflit |
| UC-05 commande idempotente | Meme `Idempotency-Key` + meme payload retourne le meme `orderId`; payload different retourne conflit |
| UC-06 paiement exactly-once pratique | Cle d'idempotence paiement, contrainte de paiement reussi unique par facture, replay retourne le meme `paymentId` |
| Audit | Evenements ecrits en append-only, visibles par `TraceId` |

## 7.2 Securite applicative et gestion d'erreurs

### Mecanismes implementes

| Sujet | Implementation Phase 1 |
|---|---|
| Authentification | UC-02 login + MFA; les endpoints sensibles utilisent `Authorization: Bearer <sessionToken>` |
| MFA | OTP de demonstration retourne par l'API en mode developpement pour rendre la demo reproductible |
| Erreurs normalisees | Reponses JSON avec `code`, `message`, `traceId`, `timestamp` et `details` lorsque disponible |
| Validation entree | Validation des champs requis, email, types de client, documents d'identite simules, `simType`, `numberMode`, montants de paiement |
| Idempotency-Key | Obligatoire pour UC-03, UC-05, UC-06 |
| Secrets | Valeurs configurees par `.env` / `.env.example`; pas de secrets reels a committer |
| Logs structures | Logs JSON avec `TraceId` pour suivre une requete entre services |
| Audit conformite | `svc-conformite-audit` conserve les evenements append-only |

### Controles anti-fraude Phase 1

Le cahier mentionne SIM swap, usage anormal et fraude avancee. La detection complete correspond a UC-07, hors perimetre officiel. Pour Phase 1, le projet garde seulement les controles necessaires aux UC retenus:

- MFA obligatoire avant session.
- Compte temporairement bloque apres trop d'echecs MFA/login lorsque couvert par les tests.
- Evaluation de risque simple par signaux de connexion et `riskLevel`.
- Blocage des clients `riskLevel=HIGH` pour UC-03 activation et UC-05 commande.
- Validation basique SIM/eSIM et MSISDN pour limiter les doublons.
- Audit des tentatives, refus et actions sensibles.

La detection d'usage anormal et un moteur de fraude complet sont documentes comme evolution future, pas comme fonctionnalites livrees.

### Verifications negatives a demontrer

| Verification | Resultat attendu |
|---|---|
| UC-03 sans `Idempotency-Key` | `400` erreur normalisee |
| UC-05 sans `Idempotency-Key` | `400` erreur normalisee |
| UC-06 sans `Idempotency-Key` | `400` erreur normalisee |
| Meme cle avec payload different | `409` conflit normalise |
| Client inconnu | `404` ou erreur metier normalisee |
| Offre inconnue/inactive | `404` ou `409` normalise |
| Facture deja payee avec autre cle | `409` normalise |
| Activation high-risk | refus/blocage et audit |
| Audit par `TraceId` | liste d'evenements pour la trace de demo |

## Evidence a capturer

- Capture `pytest` montrant `50 passed`.
- Capture coverage critique `application` + `domain` montrant `TOTAL 87%`.
- Capture du rapport HTML coverage `docs/evidence/coverage/htmlcov/index.html`.
- Capture E2E gateway `tests/e2e/test_gateway_flow.py` passant.
- Capture Postman ou Newman du parcours complet via Gateway; cette preuve est E2E, pas integration.
- Capture integration `tests/integration` montrant `7 passed, 1 skipped`.
- Capture optionnelle du test free5GC live avec `FREE5GC_LIVE_TEST=1` si le simulateur est disponible.
- Captures Postman/Swagger des erreurs normalisees: idempotency manquante, conflit idempotence, facture deja payee.
- Capture audit par `TraceId`.
- Capture logs Docker filtres par `TraceId`.
- Capture Locust officielle montrant 0% failures pour les UC retenus.
