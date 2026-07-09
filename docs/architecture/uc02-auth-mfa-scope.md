# UC-02 - Authentification et MFA

Ce document aligne le cas d'utilisation UC-02 avec l'implementation actuelle de `svc-clients-identite`.

## Decision Phase 1

UC-02 est implemente comme un flux en deux commandes REST:

1. `POST /v1/auth/login` valide le courriel et le mot de passe, evalue un risque de connexion simple, cree un challenge MFA `PENDING`, journalise `LOGIN_MFA_REQUIRED`, puis retourne un `challengeId`, `mfaRequired=true`, `mfaStrength`, `loginRisk` et un `devOtp` de demonstration.
2. `POST /v1/auth/mfa/verify` valide le challenge, son statut, son expiration et l'OTP, marque le challenge `VERIFIED`, journalise `MFA_VERIFIED`, puis retourne un `sessionToken` de type `dev-session-{challengeId}`.

Le facteur MFA implemente en Phase 1 est un OTP simule. WebAuthn, push notification, SMS reel et fournisseur MFA externe sont hors scope Phase 1.

## Scenario principal corrige

| Champ | Contenu |
|---|---|
| UC retenu | UC-02 - Authentification et MFA |
| Acteurs | Acteur principal: abonne ou representant PME. Acteurs secondaires: `svc-clients-identite`, repository MFA, `svc-conformite-audit`. |
| Preconditions | Le client possede un compte existant avec `status=ACTIVE`, un mot de passe hache et une identite verifiee. Les services Clients & Identite et Conformite & Audit sont disponibles. |
| Scenario principal | 1. L'utilisateur soumet son courriel et son mot de passe a `POST /v1/auth/login`. 2. Le service recherche le client par courriel et verifie le mot de passe avec le hash stocke. 3. Le service refuse la connexion si le compte n'est pas `ACTIVE` ou s'il est temporairement verrouille. 4. Le service evalue le risque de connexion a partir du niveau de risque client, du nombre d'echecs precedents et des `riskSignals` (`newDevice`, `roaming`, `unusualLocation`, `simSwapRecent`). 5. Le service remet a zero les echecs de connexion et enregistre le risque de connexion. 6. Le service cree un challenge MFA `PENDING` avec OTP simule `123456`, hash de l'OTP et expiration a 5 minutes. 7. Le service journalise `LOGIN_MFA_REQUIRED` avec `loginRisk` et `mfaStrength` (`STANDARD` ou `STEP_UP`). 8. L'utilisateur soumet `challengeId` et OTP a `POST /v1/auth/mfa/verify`. 9. Le service verifie que le challenge existe, est `PENDING`, n'est pas expire et que l'OTP correspond au hash. 10. Le service marque le challenge `VERIFIED`, journalise `MFA_VERIFIED`, et retourne une session `dev-session-{challengeId}`. |
| Scenarios alternatifs / exceptions | FA1 - Identifiants invalides: le service journalise `LOGIN_FAILED`, incremente `failed_login_attempts`, retourne `401 invalid_credentials`; au troisieme echec, `locked_until` est renseigne et `LOGIN_LOCKED` est journalise. FA2 - Compte non actif: le service retourne `403 customer_not_active`. FA3 - Compte temporairement verrouille: le service journalise `LOGIN_BLOCKED_LOCKED` et retourne `423 customer_temporarily_locked`. FA4 - MFA invalide: le service journalise `MFA_FAILED` et retourne `401 mfa_invalid`. FA5 - MFA expiree: le service journalise `MFA_EXPIRED` et retourne `422 mfa_expired`. FA6 - Challenge deja utilise ou non pending: le service retourne `409 mfa_already_used`. FA7 - Connexion a risque eleve: le service retourne `mfaStrength=STEP_UP`; en Phase 1, cela reste un OTP simule plus strictement signale, sans fournisseur MFA externe. |
| Postconditions / regles metier | Une session n'est creee qu'apres mot de passe valide et MFA verifie. Les challenges MFA sont a usage unique logique: un challenge verifie n'est plus `PENDING`. Les tentatives significatives sont auditees. Les tokens de session Phase 1 sont des tokens de demonstration introspectes par le gateway via `GET /v1/auth/introspect`. |

## Ajustements par rapport au scenario initial

### A garder

- Validation des identifiants.
- Evaluation du risque de connexion.
- Demande de second facteur MFA.
- Validation du MFA avant creation de session.
- Journalisation des connexions et echecs importants.
- Verrouillage temporaire apres trop d'echecs.
- Facteur renforce pour contexte a risque eleve.

### A modifier

- Remplacer "OTP, WebAuthn ou autre facteur accepte" par "OTP simule Phase 1".
- Preciser que le code OTP de demo est `123456` et retourne dans `devOtp`.
- Preciser que `STEP_UP` est un niveau de force MFA signale dans la reponse, pas une integration WebAuthn/SMS reelle.
- Ajouter les erreurs exactes implementees: `invalid_credentials`, `customer_not_active`, `customer_temporarily_locked`, `mfa_invalid`, `mfa_expired`, `mfa_already_used`.

### A retirer ou mettre en futur

- Fournisseur MFA externe reel.
- WebAuthn reel.
- Notification push ou SMS reel.
- Session de production signee/JWT/OIDC. Phase 1 utilise `dev-session-{challengeId}`.

## References implementation

- Endpoints: `POST /v1/auth/login`, `POST /v1/auth/mfa/verify`, `GET /v1/auth/introspect`
- Use cases: `services/svc-clients-identite/app/application/commands/login.py`, `services/svc-clients-identite/app/application/commands/verify_mfa.py`
- Route REST: `services/svc-clients-identite/app/adapters/inbound/rest/routes.py`
- Tests: `services/svc-clients-identite/tests/test_auth_mfa.py`
- Diagramme: `docs/architecture/diagrams/sequence-uc02-auth-mfa.puml`
