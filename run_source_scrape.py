"""Quellen-Scrape: die Profil-Liste aus clients/<name>/influencers.csv nach
Supabase, als Themenquelle fuer run_topic_mining.py.

Eigener Einstieg statt run_research.py, weil der Tages-Lauf nach dem Scrapen
den Winner-/Draft-Pfad faehrt und tools/notion_db.py die DB-ID aus der Env
liest, bevor der Mandant greift: ein CLIENT=swot-Lauf ueber run_research
schriebe seinen Entwurf in Jollys Recycling-DB.

    CLIENT=swot python run_source_scrape.py                      # Fenster aus dem SCRAPE-Block
    CLIENT=swot python run_source_scrape.py --max-age-hours 720  # Seed-Lauf ueber 30 Tage
    CLIENT=swot python run_source_scrape.py --no-write           # nur scrapen, nichts schreiben
"""
import argparse
import sys

import tools.linkedin_scraper as scraper
from clients import load_client
from tools.linkedin_scraper import scrape_new_posts
from tools.supabase_db import upsert_posts

_cfg = load_client()


def scrape_and_persist(max_age_hours: int | None = None, write: bool = True) -> int:
    """Scrapt die Quellenliste und upsertet nach Supabase (source=linkedin).
    Gibt die Zahl geschriebener Zeilen zurueck.

    max_age_hours weitet Altersfilter UND Fetch-Fenster gemeinsam: fetch_window_start
    liest dieselbe Modulkonstante, sonst holt der Actor 30 Tage und der Filter wirft
    alles ueber 168h wieder weg — bezahlt und verworfen.

    Zwei Eingriffe an der Zeitmarke, beide gemessen noetig:
    1. Ein geweitetes Fenster ignoriert sie. fetch_window_start nimmt sonst die
       ENGERE der beiden Grenzen, und die Zeitmarke des letzten Laufs macht jeden
       Seed-Lauf zum Leerlauf (gemessen 20.08.: 0 Posts trotz 720h).
    2. Ein Trockenlauf schreibt sie nicht. Sonst verbrennt er das Fenster fuer den
       echten Lauf, der danach nichts mehr sieht.
    """
    if max_age_hours:
        scraper.MAX_AGE_HOURS = max_age_hours
    original_read, original_write = scraper.read_watermark, scraper.write_watermark
    if max_age_hours:
        scraper.read_watermark = lambda: None
    if not write:
        scraper.write_watermark = lambda started_at: None
    try:
        # existing_urls bleibt leer: der Dedup gehoert hier zu Supabase
        # (on_conflict client,post_url), nicht zu einer Notion-Winner-Liste.
        posts = scrape_new_posts(existing_urls=set())
    finally:
        scraper.read_watermark, scraper.write_watermark = original_read, original_write
    print(f"  Quellen-Scrape: {len(posts)} Posts im Fenster.")
    if not write:
        print("  --no-write: kein Supabase-Upsert.")
        return 0
    n = upsert_posts(posts, source="linkedin")
    print(f"  Supabase: {n} Posts persistiert (source=linkedin).")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-age-hours", type=int, default=None,
                    help="Altersfenster ueberschreiben (Default: SCRAPE-Block des Mandanten)")
    ap.add_argument("--no-write", action="store_true", help="nur scrapen, kein Upsert")
    args = ap.parse_args()

    quellen = _cfg.INFLUENCERS_CSV
    print(f"Client: {_cfg.NAME} | Quellenliste: {quellen}")
    print(f"Fenster: {args.max_age_hours or scraper.MAX_AGE_HOURS}h, "
          f"max {scraper.MAX_POSTS_PER_PROFILE} Posts/Profil", flush=True)
    try:
        scrape_and_persist(max_age_hours=args.max_age_hours, write=not args.no_write)
    except Exception as e:
        print(f"  FEHLER: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
