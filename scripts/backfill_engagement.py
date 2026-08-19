"""Einmaliger Backfill der Engagement-Zahlen fuer bereits veroeffentlichte Posts.

Der Tageslauf misst nur das laufende Monatsfenster (cfg.ENGAGEMENT_READBACK).
Die Altbestaende liegen davor: jolly hat veroeffentlichte Zeilen ab April 2026.
Dieses Script fahrt denselben Readback einmalig mit weitem Fenster.

Kostet einen Apify-Run. Run with CLIENT=<name>.
"""
import argparse
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients import load_client
from tools.engagement_readback import run_readback


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-posts", type=int, default=150,
                    help="maxPosts pro Profil (default 150)")
    ap.add_argument("--posted-limit", default="any",
                    choices=["any", "24h", "week", "month", "3months", "6months", "year"],
                    help="Scrape-Fenster (default any)")
    args = ap.parse_args()

    cfg = load_client()
    # Nur das Fenster wird ueberschrieben, alles andere bleibt der echte Mandant.
    override = SimpleNamespace(
        ENGAGEMENT_READBACK={"max_posts_per_profile": args.max_posts,
                             "posted_limit": args.posted_limit},
        OWN_PROFILES=cfg.OWN_PROFILES,
    )
    print(f"Backfill: {args.max_posts} Posts/Profil, Fenster '{args.posted_limit}'.")
    result = run_readback(override)
    print(f"Fertig: {result['matched']}/{result['rows']} Zeilen mit Zahlen.")


if __name__ == "__main__":
    main()
