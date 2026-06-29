"""
Conteneur "fournisseur" : simule un consommateur externe qui interroge
l'UDM (Unified Data Management) du coeur 5G free5GC, via le reseau Docker.

L'appel suit l'interface SBI 3GPP Nudm_SDM (TS 29.503) :
    GET /nudm-sdm/v2/{supi}/am-data   -> donnees Access & Mobility de l'abonne

Points cles demontres :
  - communication conteneur-a-conteneur par NOM DE SERVICE (pas localhost)
  - appel SBI en HTTP/2 (httpx)
  - identification de l'abonne par son SUPI (imsi-<MCC><MNC><MSIN>)
"""

import json
import os
import sys
import time

import httpx

UDM_BASE_URL = os.getenv("UDM_BASE_URL", "http://udm.free5gc.org:8000")
SUPI = os.getenv("SUPI", "imsi-208930000000001")
PLMN_MCC = os.getenv("PLMN_MCC", "208")
PLMN_MNC = os.getenv("PLMN_MNC", "93")

# plmn-id est un parametre de requete obligatoire pour am-data : un objet
# JSON {mcc, mnc} encode dans l'URL.
PLMN_ID = json.dumps({"mcc": PLMN_MCC, "mnc": PLMN_MNC}, separators=(",", ":"))


def wait_for_udm(client: httpx.Client, retries: int = 30, delay: float = 2.0) -> None:
    """Attend que l'UDM reponde (le temps qu'elle s'enregistre aupres du NRF)."""
    url = f"{UDM_BASE_URL}/nudm-sdm/v2/{SUPI}/am-data?plmn-id={PLMN_ID}"
    for attempt in range(1, retries + 1):
        try:
            r = client.get(url)
            # Tant qu'on obtient UNE reponse HTTP, l'UDM est joignable.
            print(f"[fournisseur] UDM joignable (tentative {attempt}) "
                  f"-> HTTP {r.status_code}")
            return
        except httpx.HTTPError as exc:
            print(f"[fournisseur] UDM injoignable (tentative {attempt}/{retries}) : "
                  f"{exc.__class__.__name__}")
            time.sleep(delay)
    print("[fournisseur] ERREUR : UDM toujours injoignable, abandon.")
    sys.exit(1)


def query_am_data(client: httpx.Client) -> None:
    """Recupere les donnees Access & Mobility de l'abonne via l'UDM."""
    url = f"{UDM_BASE_URL}/nudm-sdm/v2/{SUPI}/am-data?plmn-id={PLMN_ID}"
    print(f"\n[fournisseur] GET {url}")
    r = client.get(url, headers={"Accept": "application/json"})

    print(f"[fournisseur] Statut HTTP : {r.status_code} "
          f"(protocole {r.http_version})")

    if r.status_code == 200:
        print("[fournisseur] Donnees d'abonnement recues :")
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    elif r.status_code == 404:
        print("[fournisseur] Abonne introuvable. As-tu cree le SUPI "
              f"{SUPI} dans la WebUI (http://localhost:5000) ?")
    else:
        print("[fournisseur] Reponse inattendue :")
        print(r.text)


def main() -> None:
    print(f"[fournisseur] Cible UDM : {UDM_BASE_URL}")
    print(f"[fournisseur] SUPI      : {SUPI}")
    print(f"[fournisseur] PLMN      : MCC={PLMN_MCC} MNC={PLMN_MNC}")

    # http2=True : les interfaces SBI 3GPP utilisent HTTP/2.
    with httpx.Client(http2=True, timeout=10.0) as client:
        wait_for_udm(client)
        query_am_data(client)


if __name__ == "__main__":
    main()
