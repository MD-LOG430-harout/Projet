# CanTelcoX internal event contracts

The eleven directories in this tree are the authoritative internal event
contracts for Phase 2. Each event uses one Kafka topic and the common envelope
embedded in its versioned JSON Schema.

| Event type | Topic | Producer |
|---|---|---|
| `CommandePassee` | `commande-passee.v1` | `svc-commandes-activations` |
| `PaiementAutorise` | `paiement-autorise.v1` | `svc-usage-facturation` |
| `PaiementRefuse` | `paiement-refuse.v1` | `svc-usage-facturation` |
| `PaiementRembourse` | `paiement-rembourse.v1` | `svc-usage-facturation` |
| `LigneActivee` | `ligne-activee.v1` | `svc-lignes-services` |
| `ActivationEchouee` | `activation-echouee.v1` | `svc-lignes-services` |
| `CommandeConfirmee` | `commande-confirmee.v1` | `svc-commandes-activations` |
| `CommandeAnnulee` | `commande-annulee.v1` | `svc-commandes-activations` |
| `PortabiliteDemandee` | `portabilite-demandee.v1` | `svc-lignes-services` |
| `NumeroPorte` | `numero-porte.v1` | `svc-lignes-services` |
| `PortabiliteEchouee` | `portabilite-echouee.v1` | `svc-lignes-services` |

Within v1, payload evolution is additive: new fields must be optional. Removing
or reinterpreting a field, changing its type, or making an optional field
mandatory requires a new major version and topic.

