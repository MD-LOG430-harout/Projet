"""
usage-api — façade REST d'usage (charging) free5GC.

Encapsule la collection MongoDB `cantelcox_usage` derrière une petite API REST,
pour que le BSS (CanTelcoX / usage-billing) n'accède plus directement à MongoDB.
C'est le pendant « lecture/écriture d'usage » de ce qu'est la WebConsole pour le
provisioning : une passerelle entre le cœur 5G et le BSS.

LECTURE (consommée par CanTelcoX)
  GET    /usage/{msisdn}                       -> [ {msisdn,type,quantity,recordedAt}, ... ]
  GET    /usage/{msisdn}/summary?cycle=YYYY-MM -> { msisdn, cycle, voiceSeconds, smsCount, dataBytes }

ÉCRITURE (simulation de CDR — joue le rôle du CHF)
  POST   /usage/{msisdn}            body {type, quantity, recordedAt?}  -> insère 1 CDR
  POST   /usage/{msisdn}/simulate?count=N&days=D                       -> génère N CDR aléatoires
  DELETE /usage/{msisdn}                                               -> purge l'usage d'un numéro (reset test)

  GET    /health
"""
import os
import random
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient, DESCENDING

MONGO_URI = os.getenv("MONGO_URI", "mongodb://db:27017/free5gc")
DB_NAME = os.getenv("MONGO_DB", "free5gc")
COLLECTION = os.getenv("MONGO_COLLECTION", "cantelcox_usage")
VALID_TYPES = {"VOICE", "SMS", "DATA"}

app = FastAPI(title="CanTelcoX — Usage API (free5GC charging façade)", version="1.1")
_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000)
_col = _client[DB_NAME][COLLECTION]


def _iso(v):
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc).isoformat()
    return str(v) if v is not None else None


def _parse(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


class CdrIn(BaseModel):
    """Un Charging Data Record à injecter."""
    type: str                      # VOICE | SMS | DATA
    quantity: int                  # secondes (VOICE) | nombre (SMS) | octets (DATA)
    recordedAt: str | None = None  # ISO 8601 ; défaut = maintenant


# ----------------------------------------------------------------- LECTURE

@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/usage/{msisdn}")
def usage(msisdn: str):
    """Détail des enregistrements d'usage d'un numéro (UC-04)."""
    docs = _col.find({"msisdn": msisdn}).sort("recordedAt", DESCENDING)
    return [
        {
            "msisdn": msisdn,
            "type": d.get("type", "DATA"),
            "quantity": int(d.get("quantity", 0) or 0),
            "recordedAt": _iso(d.get("recordedAt")),
        }
        for d in docs
    ]


@app.get("/usage/{msisdn}/summary")
def summary(msisdn: str, cycle: str | None = None):
    """Agrégat par type pour la facturation (UC-08). `cycle` (YYYY-MM) optionnel."""
    voice_sec = sms = data_bytes = 0
    for d in _col.find({"msisdn": msisdn}):
        if cycle:
            ts = d.get("recordedAt")
            if isinstance(ts, datetime) and ts.strftime("%Y-%m") != cycle:
                continue
        qty = int(d.get("quantity", 0) or 0)
        t = d.get("type", "DATA")
        if t == "VOICE":
            voice_sec += qty
        elif t == "SMS":
            sms += qty
        elif t == "DATA":
            data_bytes += qty
    return {"msisdn": msisdn, "cycle": cycle,
            "voiceSeconds": voice_sec, "smsCount": sms, "dataBytes": data_bytes}


# ---------------------------------------------------------------- ÉCRITURE

@app.post("/usage/{msisdn}", status_code=201)
def add_cdr(msisdn: str, cdr: CdrIn):
    """Insère un CDR unique (simulation du CHF)."""
    t = cdr.type.upper()
    if t not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {sorted(VALID_TYPES)}")
    ts = _parse(cdr.recordedAt) or datetime.now(timezone.utc)
    doc = {"msisdn": msisdn, "type": t, "quantity": int(cdr.quantity), "recordedAt": ts}
    _col.insert_one(doc)
    return {"msisdn": msisdn, "type": t, "quantity": int(cdr.quantity), "recordedAt": _iso(ts)}


@app.post("/usage/{msisdn}/simulate", status_code=201)
def simulate(msisdn: str, count: int = 10, days: int = 30):
    """Génère `count` CDR aléatoires répartis sur les `days` derniers jours."""
    now = datetime.now(timezone.utc)
    docs = []
    for _ in range(max(0, count)):
        t = random.choice(("VOICE", "SMS", "DATA"))
        qty = {"VOICE": random.randint(30, 1800),
               "SMS": 1,
               "DATA": random.randint(1_000_000, 500_000_000)}[t]
        ts = now - timedelta(minutes=random.randint(0, max(1, days) * 24 * 60))
        docs.append({"msisdn": msisdn, "type": t, "quantity": qty, "recordedAt": ts})
    if docs:
        _col.insert_many(docs)
    return {"msisdn": msisdn, "inserted": len(docs)}


@app.delete("/usage/{msisdn}")
def reset(msisdn: str):
    """Purge l'usage d'un numéro (réinitialisation des jeux de test)."""
    r = _col.delete_many({"msisdn": msisdn})
    return {"msisdn": msisdn, "deleted": r.deleted_count}
