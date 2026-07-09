# UC-01 - Inscription et verification d'identite

Ce document aligne le cas d'utilisation UC-01 avec l'implementation actuelle de `svc-clients-identite`.

## Decision Phase 1

UC-01 est implemente comme une inscription avec verification d'identite simulee synchrone. Le service valide les donnees minimales, verifie l'unicite de l'adresse courriel, hache le document d'identite et le mot de passe, cree le client directement avec `status=ACTIVE`, `identityStatus=VERIFIED` et `riskLevel=LOW`, puis journalise `CUSTOMER_REGISTERED`.

La validation OTP/MFA n'appartient pas a UC-01 dans l'implementation Phase 1. Elle est couverte par UC-02 avec `POST /v1/auth/login` et `POST /v1/auth/mfa/verify`.

## Scenario principal corrige

| Champ | Contenu |
|---|---|
| UC retenu | UC-01 - Inscription et verification d'identite |
| Acteurs | Acteur principal: abonne particulier ou representant PME. Acteurs secondaires: `svc-clients-identite`, `svc-conformite-audit`. |
| Preconditions | L'abonne n'a pas encore de compte avec la meme adresse courriel. Les services Clients & Identite et Conformite & Audit sont disponibles. |
| Scenario principal | 1. L'abonne soumet ses informations d'inscription: courriel, mot de passe, nom affiche, nom legal, adresse canadienne, type et numero de document d'identite simule, type de client. 2. Le service valide les champs obligatoires, le format du courriel, la longueur du mot de passe, la province canadienne, le code postal et le document d'identite simule. 3. Le service verifie qu'aucun client n'existe deja avec le meme courriel. 4. Le service applique une verification d'identite simulee synchrone de Phase 1. 5. Le numero de document d'identite et le mot de passe sont haches avant persistance. 6. Le service cree le profil client avec `status=ACTIVE`, `identityStatus=VERIFIED` et `riskLevel=LOW`. 7. Le service journalise un evenement `CUSTOMER_REGISTERED` avec `TraceId`, source, resultat, statut d'identite et niveau de risque. 8. Le service retourne `201 Created` avec le profil public du client, sans exposer le numero de document ni le hash du mot de passe. |
| Scenarios alternatifs / exceptions | FA1 - Donnees invalides: le service retourne `400 validation_error` sans creer de client. FA2 - Courriel deja utilise: le service retourne `409 customer_exists` sans creer de doublon. FA3 - Service audit indisponible: en environnement Compose normal, `svc-clients-identite` depend du service audit healthy; si l'appel audit echoue pendant la requete, l'erreur technique est propagee et doit etre traitee comme indisponibilite transitoire. FA4 - Verification avancee KYC ou risque eleve: non implementee comme workflow asynchrone Phase 1; documentee comme extension future. |
| Postconditions / regles metier | Un client est cree seulement si les donnees minimales sont valides et le courriel unique. Les donnees sensibles ne sont pas stockees en clair. L'inscription reussie est auditee. MFA et OTP sont traites separement par UC-02. |

## Ecart avec le scenario initial

Le scenario initial mentionnait un statut `Pending`, une verification KYC asynchrone et une confirmation OTP/MFA dans UC-01. Ces etapes ne correspondent pas au code Phase 1. Elles sont remplacees par une verification simulee synchrone, et MFA est deplace vers UC-02.

## References implementation

- Endpoint: `POST /v1/customers/register`
- Use case: `services/svc-clients-identite/app/application/commands/register_customer.py`
- Route REST: `services/svc-clients-identite/app/adapters/inbound/rest/routes.py`
- Tests: `services/svc-clients-identite/tests/test_registration.py`
- Diagramme: `docs/architecture/diagrams/sequence-uc01-registration.puml`
