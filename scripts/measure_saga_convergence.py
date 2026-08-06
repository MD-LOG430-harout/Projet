#!/usr/bin/env python3
"""Measure Saga A (order placement) end-to-end convergence.

Reads services/svc-commandes-activations's saga_state table (created_at acts as
started_at, completed_at is set when the saga reaches CONFIRMEE or ANNULEE) and
reports:
  - P95 duration for nominal sagas (CONFIRMEE)      -- target: <= 3.0 s
  - P95 duration for compensated sagas (ANNULEE)     -- target: <= 5.0 s
  - the share of sagas that reached a terminal state -- target: 100 %

No extra Python dependency: shells out to `docker exec` against the running
mysql container, same as the manual queries used throughout this project's
load-test campaigns.

Usage:
    python scripts/measure_saga_convergence.py
"""
import subprocess
import sys

MYSQL_CONTAINER = "projet-mysql-1"
MYSQL_USER = "cantelcox"
MYSQL_PASSWORD = "cantelcox_dev"
DATABASE = "commandes_activations"

NOMINAL_TARGET_SECONDS = 3.0
COMPENSATION_TARGET_SECONDS = 5.0
CONVERGENCE_TARGET_PERCENT = 100.0


def run_query(sql):
    result = subprocess.run(
        [
            "docker", "exec", MYSQL_CONTAINER,
            "mysql", f"-u{MYSQL_USER}", f"-p{MYSQL_PASSWORD}", "-N", "-B", DATABASE,
            "-e", sql,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.split("\t") for line in result.stdout.strip().splitlines() if line]


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def durations_for(status):
    rows = run_query(
        "SELECT TIMESTAMPDIFF(MICROSECOND, created_at, completed_at) / 1000000.0 "
        f"FROM saga_state WHERE status='{status}' AND completed_at IS NOT NULL"
    )
    return [float(row[0]) for row in rows]


def convergence_rate():
    rows = run_query(
        "SELECT COUNT(*), "
        "SUM(status IN ('CONFIRMEE','ANNULEE')), "
        "SUM(status NOT IN ('CONFIRMEE','ANNULEE')) "
        "FROM saga_state"
    )
    total, terminal, non_terminal = (int(value) for value in rows[0])
    rate = (terminal / total * 100) if total else 0.0
    return total, terminal, non_terminal, rate


def label(ok):
    return "ATTEINT" if ok else "NON ATTEINT"


def main():
    nominal = durations_for("CONFIRMEE")
    compensated = durations_for("ANNULEE")
    total, terminal, non_terminal, rate = convergence_rate()

    p95_nominal = percentile(nominal, 95)
    p95_compensated = percentile(compensated, 95)

    all_ok = True

    print("=== Convergence de la Saga A (Prise de commande) ===\n")

    print(f"Sagas nominales (CONFIRMEE) : {len(nominal)} echantillons")
    if p95_nominal is not None:
        ok = p95_nominal <= NOMINAL_TARGET_SECONDS
        all_ok &= ok
        print(f"  P95 = {p95_nominal:.3f} s (cible <= {NOMINAL_TARGET_SECONDS} s) -> {label(ok)}")
    else:
        print("  Aucune donnee -- lancer une campagne nominale (POST /v1/orders) d'abord.")
        all_ok = False

    print(f"\nSagas compensees (ANNULEE) : {len(compensated)} echantillons")
    if p95_compensated is not None:
        ok = p95_compensated <= COMPENSATION_TARGET_SECONDS
        all_ok &= ok
        print(f"  P95 = {p95_compensated:.3f} s (cible <= {COMPENSATION_TARGET_SECONDS} s) -> {label(ok)}")
    else:
        print("  Aucune donnee -- relancer avec PAYMENT_GATEWAY_FORCE_REFUSAL=true pour forcer la compensation.")
        all_ok = False

    print(f"\nConvergence globale : {terminal}/{total} sagas terminales ({rate:.4f} %)")
    print(f"  Non terminales (orphelines) : {non_terminal}")
    ok = rate >= CONVERGENCE_TARGET_PERCENT
    all_ok &= ok
    print(f"  -> {label(ok)} (cible = {CONVERGENCE_TARGET_PERCENT} %)")

    print()
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
