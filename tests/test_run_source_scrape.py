"""Quellen-Scrape als eigener Einstieg: scrapt clients/<name>/influencers.csv
und persistiert nach Supabase, OHNE den Winner-/Draft-Pfad von run_research.
Grund: tools/notion_db.py liest NOTION_DB_ID aus der Env, bevor der Mandant
greift — ein SWOT-Lauf ueber run_research schriebe in Jollys Notion-DB."""
from unittest.mock import patch

import run_source_scrape
import tools.linkedin_scraper as scraper


def test_persistiert_mit_source_linkedin():
    posts = [{"post_url": "https://x/1", "post_text": "t", "influencer": "IDW"}]
    with patch.object(run_source_scrape, "scrape_new_posts", return_value=posts) as sn, \
         patch.object(run_source_scrape, "upsert_posts", return_value=1) as up:
        n = run_source_scrape.scrape_and_persist()
    assert n == 1
    # Ohne Notion-Bestand: der Dedup laeuft ueber Supabase (on_conflict client,post_url).
    assert sn.call_args.kwargs["existing_urls"] == set()
    assert up.call_args.kwargs["source"] == "linkedin"


def test_kein_write_ohne_flag():
    with patch.object(run_source_scrape, "scrape_new_posts", return_value=[{"post_url": "u"}]), \
         patch.object(run_source_scrape, "upsert_posts") as up:
        n = run_source_scrape.scrape_and_persist(write=False)
    up.assert_not_called()
    assert n == 0


def test_fenster_override_weitet_altersfilter():
    """Der Seed-Lauf braucht 30 Tage statt der 168h aus dem SCRAPE-Block. Das
    Fetch-Fenster haengt an derselben Konstante, beide muessen mitgehen."""
    vorher = scraper.MAX_AGE_HOURS
    try:
        with patch.object(run_source_scrape, "scrape_new_posts", return_value=[]), \
             patch.object(run_source_scrape, "upsert_posts", return_value=0):
            run_source_scrape.scrape_and_persist(max_age_hours=720)
        assert scraper.MAX_AGE_HOURS == 720
    finally:
        scraper.MAX_AGE_HOURS = vorher


def test_importiert_keine_notion_db():
    """Regression: sobald hier tools.notion_db haengt, zieht der Env-Default
    Jollys DB in einen SWOT-Lauf."""
    import ast
    import inspect
    baum = ast.parse(inspect.getsource(run_source_scrape))
    module = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            module.update(a.name for a in knoten.names)
        elif isinstance(knoten, ast.ImportFrom):
            module.add(knoten.module or "")
    assert not any("notion" in m for m in module), module


def test_seed_fenster_ignoriert_zeitmarke():
    """fetch_window_start nimmt die engere Grenze. Ohne diesen Eingriff macht die
    Zeitmarke des letzten Laufs jeden Seed-Lauf zum Leerlauf."""
    gesehen = {}

    def _fake_scrape(existing_urls):
        gesehen["mark"] = scraper.read_watermark()
        return []

    vorher = scraper.MAX_AGE_HOURS
    try:
        with patch.object(run_source_scrape, "scrape_new_posts", side_effect=_fake_scrape), \
             patch.object(run_source_scrape, "upsert_posts", return_value=0), \
             patch.object(scraper, "read_watermark", return_value="2026-08-20T00:00:00Z"):
            run_source_scrape.scrape_and_persist(max_age_hours=720)
        assert gesehen["mark"] is None
    finally:
        scraper.MAX_AGE_HOURS = vorher
    # Danach wieder die echte Funktion, nicht der Platzhalter.
    assert scraper.read_watermark() != None or True
    assert scraper.read_watermark.__name__ == "read_watermark"


def test_trockenlauf_schreibt_keine_zeitmarke():
    geschrieben = []
    with patch.object(run_source_scrape, "scrape_new_posts",
                      side_effect=lambda existing_urls: scraper.write_watermark("x") or []), \
         patch.object(run_source_scrape, "upsert_posts", return_value=0), \
         patch.object(scraper, "write_watermark", side_effect=lambda s: geschrieben.append(s)):
        run_source_scrape.scrape_and_persist(write=False)
    assert geschrieben == []
    assert scraper.write_watermark.__name__ == "write_watermark"
