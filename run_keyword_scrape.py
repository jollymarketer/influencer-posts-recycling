"""Keyword-based LinkedIn scrape -> Supabase mining store.

Scrapes LinkedIn posts for Jolly's locked target keywords (the topics jolly wants to rank / be
cited for) and upserts them into blog_content_mining.influencer_posts with source="linkedin_search".
The existing weekly Friday clustering (run_topic_mining.py) then turns them into Topic-Idea
candidates alongside the influencer-profile posts.

Standalone / on-demand. Does NOT touch the daily run_research flow.

    python run_keyword_scrape.py                       # full run, defaults
    python run_keyword_scrape.py --max-posts 10        # cheaper
    python run_keyword_scrape.py --keywords "revops" "cold email"   # subset (verification run)
    python run_keyword_scrape.py --no-write            # scrape only, skip Supabase upsert
"""
import argparse
import os
import sys

from clients import load_client
from tools.linkedin_keyword_scraper import scrape_keyword_posts
from tools.supabase_db import upsert_posts

def _jolly_axes() -> dict:
    """Achsen-Abbildung aus jollys Config, ohne den CLIENT der Laufzeit
    anzufassen: JOLLY_KEYWORDS ist ein Modul-Attribut und wird auch dann
    gelesen, wenn ein anderer Mandant laeuft."""
    from clients.jolly import config as jolly_config
    return jolly_config.KEYWORDS_BY_AXIS


# Locked 2026-06-08 with Richard. Derived from the AI-visibility scoreboard gaps + beachheads.
# Commercial pillars + mechanism long-tails + AI/KI-applied-to-GTM. No HubSpot, no cold calling.
# Seit 2026-09-22 abgeleitet aus clients/jolly/config.py KEYWORDS_BY_AXIS: die 18 gelockten
# Begriffe wurden dort auf Achsen verteilt, nicht ersetzt, und um 36 erweitert. Nicht wieder
# als Literal zurueckdrehen, sonst traegt die Achse eine zweite Wahrheit.
JOLLY_KEYWORDS = [k for keywords in _jolly_axes().values() for k in keywords]


def axis_for_keyword(keyword: str, cfg=None) -> str | None:
    """Umkehrung von KEYWORDS_BY_AXIS: Begriff nach Achse, ohne Ruecksicht auf
    Gross- und Kleinschreibung. Unbekannter Begriff -> None (der Klassifizierer
    holt die Zeile spaeter, keine Zuordnung auf Verdacht)."""
    by_axis = getattr(cfg, "KEYWORDS_BY_AXIS", None) if cfg else _jolly_axes()
    if not by_axis:
        return None
    ziel = keyword.strip().lower()
    for achse, keywords in by_axis.items():
        if ziel in {k.lower() for k in keywords}:
            return achse
    return None

# Server-side author-headline filter. NOTE: the actor treats authorKeywords as a SINGLE term, not a
# multi-term OR-list (a space/comma list returns 0 results). So this is disabled by default; pass a
# single broad term via --author-keywords (e.g. "sales") if you want it. Off-industry/hiring noise is
# better handled post-scrape (see virality filter + downstream clusterer).
AUTHOR_KEYWORDS = ""


def resolve_keywords(cfg, client_name: str) -> list:
    """Keyword-Set des Mandanten. JOLLY_KEYWORDS ist jollys eigene, am 08.06.2026
    gelockte Liste und gilt NUR fuer jolly. Jeder andere Mandant muss KEYWORDS in
    seiner clients/<name>/config.py definieren - kein stiller Fallback, sonst
    scrapt ein Fremdmandant gegen jollys Themen (Richard, 19.08.2026)."""
    own = getattr(cfg, "KEYWORDS", None)
    if own:
        return list(own)
    if client_name == "jolly":
        return list(JOLLY_KEYWORDS)
    raise SystemExit(
        f"Abbruch: Mandant '{client_name}' hat keine KEYWORDS in clients/{client_name}/config.py. "
        f"JOLLY_KEYWORDS gilt nur fuer jolly."
    )


_CLIENT = os.getenv("CLIENT", "jolly").strip().lower()


def client_keywords() -> list:
    """Aufloesung erst beim Aufruf, nicht beim Import.

    Bis 19.08.2026 stand hier `KEYWORDS = resolve_keywords(...)` auf
    Modulebene. run_research importiert dieses Modul unbedingt, also ist damit
    JEDER Mandant ohne eigene KEYWORDS schon am blossen Import gestorben, auch
    wenn er gar nicht scrapt. Das traf lisocon (FEATURES["keyword_scrape"] =
    False) und legte dessen Railway-Lauf lahm. Nicht auf Modulebene
    zurueckdrehen."""
    return resolve_keywords(load_client(), _CLIENT)


def scrape_and_persist(keywords=None, max_posts=20, posted_limit="month",
                       min_virality=5, author_keywords=AUTHOR_KEYWORDS) -> int:
    """Scrape the keyword set and upsert to Supabase (source=linkedin_search). Returns rows written.
    Reused by the CLI and by run_research's weekly cadence branch.

    Je Begriff ein eigener Upsert, damit die Achse aus axis_for_keyword mitgeht.
    Ohne das schrieb der Donnerstags-Lauf achsenlose Zeilen, die der
    Klassifizierer danach bezahlt nachsortieren musste, obwohl die Herkunft
    bekannt war."""
    ziel = list(keywords or client_keywords())
    gesamt = 0
    for keyword in ziel:
        posts = scrape_keyword_posts(
            [keyword], max_posts=max_posts, posted_limit=posted_limit,
            min_virality=min_virality, author_keywords=author_keywords,
        )
        if not posts:
            continue
        achse = axis_for_keyword(keyword)
        n = upsert_posts(posts, source="linkedin_search", axis=achse)
        print(f"  keyword-scrape '{keyword}': {len(posts)} posts, {n} persisted "
              f"(axis={achse or 'unbekannt'}).")
        gesamt += n
    return gesamt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-posts", type=int, default=20, help="max posts per keyword query")
    ap.add_argument("--posted-limit", default="month", help="any|1h|24h|week|month|3months|...")
    ap.add_argument("--min-virality", type=int, default=5,
                    help="0-10 floor; drop posts below this engagement score (default 5)")
    ap.add_argument("--author-keywords", default=AUTHOR_KEYWORDS,
                    help="server-side author-headline filter (comma-separated). '' to disable.")
    ap.add_argument("--keywords", nargs="*", help="override keyword set (verification runs)")
    ap.add_argument("--no-write", action="store_true", help="scrape only, skip Supabase upsert")
    args = ap.parse_args()

    keywords = args.keywords or client_keywords()
    print(f"Scraping {len(keywords)} keyword queries, max {args.max_posts}/query, "
          f"posted_limit={args.posted_limit}, min_virality={args.min_virality}, "
          f"author_keywords={args.author_keywords!r} ...", flush=True)

    if args.no_write:
        # Vorschau-Scrape nur hier: scrape_and_persist scrapt selbst je Begriff,
        # ein vorgezogener Sammel-Scrape wuerde im Schreiblauf doppelt zahlen.
        posts = scrape_keyword_posts(
            keywords, max_posts=args.max_posts, posted_limit=args.posted_limit,
            min_virality=args.min_virality, author_keywords=args.author_keywords,
        )
        print(f"  {len(posts)} usable posts (>=50 words, virality>={args.min_virality}, deduped).")
        print("  --no-write: skipping Supabase upsert.")
        for p in sorted(posts, key=lambda x: x["virality"], reverse=True)[:15]:
            eng = p["engagement"]
            print(f"    v{p['virality']} [{eng['likes']}L/{eng['comments']}C/{eng['shares']}S] "
                  f"{p['influencer']}: {p['post_excerpt'][:55]}...")
        return 0

    try:
        n = scrape_and_persist(keywords=keywords, max_posts=args.max_posts,
                               posted_limit=args.posted_limit,
                               min_virality=args.min_virality,
                               author_keywords=args.author_keywords)
        print(f"  Supabase: {n} posts persisted (source=linkedin_search).")
    except Exception as e:
        print(f"  Supabase-Persist fehlgeschlagen: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
