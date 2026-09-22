"""Achsen-Backfill fuer jollys Pool. Nur Zeilen ohne Achsen-Entscheidung.

    python scripts/backfill_axes.py --days 90 --limit 20   # Messlauf
    python scripts/backfill_axes.py --days 90              # voller Lauf
    python scripts/backfill_axes.py --report-only          # nur Verteilung

Kosten: ein Haiku-Call je Zeile. 736 Zeilen liegen unter 1 EUR (Schaetzung
Spec 2026-09-22), der Messlauf mit --limit 20 belegt das vorher.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client
from tools.axis_classifier import classify_rows
from tools.supabase_db import axis_distribution, get_unclassified_posts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--report-only", action="store_true",
                    help="nur die Verteilung zeigen, nichts klassifizieren")
    args = ap.parse_args()

    cfg = load_client()
    print(f"Client: {cfg.NAME} | Fenster: {args.days} Tage")

    if not args.report_only:
        rows = get_unclassified_posts(args.days, limit=args.limit)
        print(f"{len(rows)} Zeilen ohne Achse. Klassifiziere ...", flush=True)
        ergebnis = classify_rows(rows, cfg=cfg)
        if not ergebnis:
            print("  Kein Lauf: FEATURES['axis_classifier'] ist nicht gesetzt.")
        for achse, n in sorted(ergebnis.items(), key=lambda x: -x[1]):
            print(f"  {achse}: {n}")

    print(f"\nVerteilung im Pool ({args.days} Tage):")
    verteilung = axis_distribution(args.days)
    summe = sum(verteilung.values()) or 1
    for achse, n in sorted(verteilung.items(), key=lambda x: -x[1]):
        print(f"  {achse}: {n} ({100 * n // summe} Prozent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
