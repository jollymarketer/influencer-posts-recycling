"""Begriffs-Scrape je Achse statt in einem Topf.

    CLIENT=swot python run_axis_scrape.py                          # alle Achsen
    CLIENT=swot python run_axis_scrape.py --axes woher_die_zahlen  # nur eine
    CLIENT=swot python run_axis_scrape.py --max-posts 50 --min-virality 2
    CLIENT=swot python run_axis_scrape.py --no-write               # nur scrapen

Warum getrennt (Richard, 20.08.2026): der Lauf vom 19.08. clusterte alle 43
Begriffe zusammen, 10 von 15 Themen wurden Liquiditaet. Die Mischregel im
Monatsplan kann aus einem schiefen Pool nichts geraderuecken, die Vielfalt muss
beim Scrapen entstehen. Jede Achse schreibt deshalb ihre eigene Herkunft:
source="linkedin_search:<achse>".

Zur Herkunft: der Supabase-Schluessel ist (client, post_url). Findet ein zweiter
Achsen-Lauf denselben Post, ueberschreibt er die Herkunft. Last write wins.

Kosten: Apify rechnet JEDEN gelieferten Post ab, --min-virality filtert erst
danach. Ein niedriger Boden holt mehr aus demselben bezahlten Material.
"""
import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.linkedin_keyword_scraper import scrape_keyword_posts
from tools.supabase_db import upsert_posts

MAX_POSTS = 20
MIN_VIRALITY = 5
POSTED_LIMIT = "month"


def axis_keywords(cfg=None) -> dict:
    cfg = cfg or load_client()
    by_axis = getattr(cfg, "KEYWORDS_BY_AXIS", None)
    if not by_axis:
        raise SystemExit(
            f"Mandant '{cfg.NAME}' hat kein KEYWORDS_BY_AXIS in "
            f"clients/{cfg.NAME}/config.py. Ohne Zuordnung kein Achsen-Scrape."
        )
    return by_axis


def run(axes=None, max_posts=MAX_POSTS, min_virality=MIN_VIRALITY,
        posted_limit=POSTED_LIMIT, write=True, cfg=None) -> dict:
    """Scrapt je Achse und upsertet mit achsenspezifischer Herkunft.
    Gibt {achse: geschriebene Zeilen} zurueck."""
    cfg = cfg or load_client()
    by_axis = axis_keywords(cfg)
    ziel = list(axes) if axes else list(by_axis)
    unbekannt = [a for a in ziel if a not in by_axis]
    if unbekannt:
        raise SystemExit(f"Unbekannte Achse(n): {unbekannt}. Bekannt: {list(by_axis)}")

    ergebnis = {}
    for achse in ziel:
        keywords = by_axis[achse]
        print(f"\n=== {achse}: {len(keywords)} Begriffe, max {max_posts}/Begriff, "
              f"Boden {min_virality} ===", flush=True)
        posts = scrape_keyword_posts(keywords, max_posts=max_posts,
                                     posted_limit=posted_limit,
                                     min_virality=min_virality)
        print(f"  {len(posts)} brauchbare Posts nach Filter.", flush=True)
        if not write:
            ergebnis[achse] = 0
            continue
        n = upsert_posts(posts, source=f"linkedin_search:{achse}")
        print(f"  {n} Zeilen nach Supabase (source=linkedin_search:{achse}).", flush=True)
        ergebnis[achse] = n
    return ergebnis


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--axes", nargs="*", help="nur diese Achsen (Default: alle)")
    ap.add_argument("--max-posts", type=int, default=MAX_POSTS,
                    help=f"max Posts je Begriff (Default {MAX_POSTS})")
    ap.add_argument("--min-virality", type=int, default=MIN_VIRALITY,
                    help=f"Engagement-Boden 0-10 (Default {MIN_VIRALITY}; 2 heisst ein Kommentar)")
    ap.add_argument("--posted-limit", default=POSTED_LIMIT, help="any|24h|week|month|3months")
    ap.add_argument("--no-write", action="store_true", help="nur scrapen, kein Upsert")
    args = ap.parse_args()

    ergebnis = run(axes=args.axes, max_posts=args.max_posts,
                   min_virality=args.min_virality, posted_limit=args.posted_limit,
                   write=not args.no_write)
    print(f"\nSumme: {sum(ergebnis.values())} Zeilen geschrieben "
          f"({len(ergebnis)} Achsen).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
