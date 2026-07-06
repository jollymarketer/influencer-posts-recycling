"""
Influencer Posts Recycling — Vollautomatischer Daily Pipeline
Railway Cron: Mo-Fr 07:00 UTC (täglich ein Winner, postet am selben Tag.
Mo-Pool = neue Posts von Fr-Nachmittag bis So; Score-Gate filtert Schwaches.)

Flow:
1. Bestehende Post-URLs aus Notion laden (Duplikat-Filter)
2. Neue Posts scrapen (LinkedIn + Substack)
3. Posts scoren (in-memory, KI + Engagement)
4. Winner waehlen (Mindest-Score: 25/60)
5. DACH-LinkedIn-Draft + Bild-Prompt generieren
6. Bild generieren (kie.ai)
7. NUR den Winner in Notion speichern (Status: "Ready to Review")

Nur 1 Post pro Tag in Notion. Verlierer werden nicht gespeichert.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

# UTF-8 stdout — Windows cp1252 kann Sonderzeichen in Influencer-Namen nicht encoden.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.notion_db import (
    get_existing_post_urls,
    get_recent_linkedin_drafts,
    get_recent_formats,
    get_recent_infographic_types,
    get_recent_archetypes,
    create_post_entry,
    update_with_draft,
)
from tools.linkedin_scraper import scrape_new_posts
from tools.substack_scraper import scrape_substack_posts
from tools.post_scorer import (
    score_posts,
    generate_post_and_image_prompt,
    pick_format,
    parse_infographic_type,
    normalize_infographic_type,
)
from tools.image_archetypes import (
    select_archetype,
    build_archetype_prompt,
    skeleton_signals,
    ARCHETYPES,
)
from tools.kieai_image import generate_image
from tools.supabase_db import upsert_posts
from run_topic_mining import run_topic_mining
from run_keyword_scrape import scrape_and_persist

MIN_SCORE = 25

_cfg = load_client()


def persist_scraped_posts(linkedin_posts: list, substack_posts: list) -> None:
    """Upsert ALL scraped posts (winners + losers) to Supabase. Non-fatal:
    a failure here must never block the daily winner/draft flow.
    Nur fuer Clients mit supabase_persist (speist das Jolly-Blog-Topic-Mining)."""
    if not _cfg.FEATURES.get("supabase_persist"):
        return
    for posts, source in ((linkedin_posts, "linkedin"), (substack_posts, "substack")):
        if not posts:
            continue
        try:
            n = upsert_posts(posts, source=source)
            print(f"  Supabase: {n} {source}-Posts persistiert.")
        except Exception as e:
            print(f"  Supabase-Persist {source} fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)


def run_daily():
    start_time = datetime.now(timezone.utc)
    print(f"=== Influencer Posts Recycling - Daily Run (Client: {_cfg.NAME}) ===")
    print(f"Start: {start_time.strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    # Schritt 1: Duplikat-Filter
    print("Schritt 1: Lade bestehende Post-URLs aus Notion ...")
    try:
        existing_urls = get_existing_post_urls()
        print(f"  {len(existing_urls)} Posts bereits bekannt.")
    except Exception as e:
        print(f"  FEHLER - Notion-Verbindung: {e}", file=sys.stderr)
        sys.exit(1)

    # Schritt 2: Neue Posts scrapen (LinkedIn + Substack)
    print("\nSchritt 2: Scrape neue Posts (LinkedIn + Substack) ...")
    new_posts = []
    linkedin_posts = []
    substack_posts = []
    try:
        linkedin_posts = scrape_new_posts(existing_urls=existing_urls)
        print(f"  LinkedIn: {len(linkedin_posts)} neue Posts")
        new_posts.extend(linkedin_posts)
    except Exception as e:
        print(f"  FEHLER - LinkedIn-Scraping: {e}", file=sys.stderr)

    try:
        substack_posts = scrape_substack_posts(existing_urls=existing_urls)
        print(f"  Substack: {len(substack_posts)} neue Artikel")
        new_posts.extend(substack_posts)
    except Exception as e:
        print(f"  FEHLER - Substack-Scraping: {e}", file=sys.stderr)

    # Persist ALL scraped posts (winners + losers) for weekly blog-topic mining.
    persist_scraped_posts(linkedin_posts, substack_posts)

    if not new_posts:
        print("  Keine neuen Posts gefunden. Run beendet.")
        return

    print(f"  Gesamt: {len(new_posts)} neue Inhalte.")

    # Schritt 3: Scoren (alles in-memory, nichts in Notion)
    print(f"\nSchritt 3: Score {len(new_posts)} Posts ...")
    try:
        recent_drafts = get_recent_linkedin_drafts(7)
        scored = score_posts(new_posts, recent_drafts=recent_drafts)
        for p in scored[:5]:
            print(f"  [{p['score']}/60] {p['influencer']}: {p.get('reasoning', '')[:80]}")
    except Exception as e:
        print(f"  FEHLER beim Scoring: {e}", file=sys.stderr)
        sys.exit(1)

    # Schritt 4: Winner waehlen
    winner = scored[0] if scored and scored[0]["score"] >= MIN_SCORE else None
    if not winner:
        top_score = scored[0]["score"] if scored else 0
        print(f"\n  Kein Post erreicht Mindest-Score {MIN_SCORE}/60 (bester: {top_score}). Run beendet.")
        return

    print(f"\nSchritt 4: Winner = {winner['influencer']} (Score: {winner['score']}/60)")

    # Schritt 4.5: Format waehlen (best-fit + anti-repeat, Pierre-Herubel Format-Varietaet)
    try:
        recent_formats = get_recent_formats()
    except Exception as e:
        print(f"  Recent-Formate laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
        recent_formats = []
    post_format = pick_format(winner, recent_formats)
    print(f"  Format gewaehlt: {post_format} (zuletzt: {recent_formats[:3]})")

    # Schritt 4.6: Zuletzt genutzte Infografik-Typen laden (Anti-Repeat gegen die
    # Eisberg-Monotonie). Non-fatal: fehlt die Property, laeuft der Run ohne Hinweis.
    try:
        recent_infographic_types = get_recent_infographic_types()
    except Exception as e:
        print(f"  Recent-Infografik-Typen laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
        recent_infographic_types = []
    if recent_infographic_types:
        print(f"  Zuletzt genutzte Infografik-Typen: {recent_infographic_types}")

    # Zuletzt genutzte Bild-Archetypen laden (Anti-Repeat des Bild-Routers).
    # Non-fatal: fehlt die Property, laeuft der Run ohne Anti-Repeat weiter.
    try:
        recent_archetypes = get_recent_archetypes()
    except Exception as e:
        print(f"  Recent-Bild-Archetypen laden fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
        recent_archetypes = []
    if recent_archetypes:
        print(f"  Zuletzt genutzte Bild-Archetypen: {recent_archetypes}")

    # Schritt 5: LinkedIn-Draft + Bild-Prompt generieren
    print("\nSchritt 5: Generiere LinkedIn-Draft + Bild-Prompt ...")
    try:
        linkedin_draft, en_draft, image_prompt, infographic_skeleton, sound_byte, kontext = generate_post_and_image_prompt(
            winner, post_format, recent_infographic_types=recent_infographic_types
        )
    except Exception as e:
        print(f"  FEHLER bei Content-Generierung: {e}", file=sys.stderr)
        sys.exit(1)

    if not linkedin_draft:
        print("  FEHLER: Leerer DE-Draft. Kein Notion-Update.", file=sys.stderr)
        sys.exit(1)

    if not en_draft:
        en_draft = "[EN-Generierung fehlgeschlagen - manuell nachziehen]"
        print("  WARNUNG: Leerer EN-Draft. Platzhalter gesetzt, DE wird gespeichert.", file=sys.stderr)

    print(f"  DE-Draft: {len(linkedin_draft)} Zeichen")
    print(f"  EN-Draft: {len(en_draft)} Zeichen")
    print(f"  Bild-Prompt: {'OK' if image_prompt else 'leer'}")
    print(f"  Infografik-Skelett: {'OK' if infographic_skeleton else 'leer'}")

    # Gewaehlten Infografik-Typ extrahieren + kanonisieren (fuer Anti-Repeat im naechsten Run)
    infographic_type = normalize_infographic_type(parse_infographic_type(infographic_skeleton))
    print(f"  Infografik-Typ: {infographic_type or 'unbekannt'}")

    # Schritt 6: Bild-Archetyp waehlen + Bild generieren. Statt immer die literale
    # Infografik zu rendern (die clunky/template-y wirkte), waehlt der Router aus 7
    # visuell verschiedenen Formen die beste fuer diesen Post — concept-forward,
    # mit Anti-Repeat gegen die letzten 2 Archetypen. Die Infografik bleibt eine
    # Option, ist aber nur bei wirklich strukturellen Posts der starke Kandidat.
    sig = skeleton_signals(infographic_skeleton, sound_byte)
    chosen_archetype = select_archetype(
        post_format=post_format,
        infographic_type=infographic_type,
        layers_count=sig["layers_count"],
        has_metaphor=sig["has_metaphor"],
        has_stat=sig["has_stat"],
        recent_archetypes=recent_archetypes,
    )
    gen_archetype, gen_prompt, gen_ratio, gen_strip = build_archetype_prompt(
        chosen_archetype,
        soundbyte=sound_byte,
        kontext=kontext,
        skeleton=infographic_skeleton,
        language="English",
    )
    gen_label = ARCHETYPES[gen_archetype]["label"]
    if gen_archetype != chosen_archetype:
        print(f"  Bild-Archetyp: {chosen_archetype} -> Fallback {gen_archetype} ({gen_label})")
    else:
        print(f"  Bild-Archetyp gewaehlt: {gen_archetype} ({gen_label})")

    image_url = ""
    image_failed = False
    image_error = ""
    if gen_prompt:
        print(f"\nSchritt 6: Generiere Bild (kie.ai, {gen_label}, {gen_ratio}) ...")
        try:
            image_url = generate_image(gen_prompt, aspect_ratio=gen_ratio, strip_marks=gen_strip)
            print(f"  Bild-URL: {image_url}")
        except Exception as e:
            image_failed = True
            image_error = str(e)
            print(f"  Bildgenerierung fehlgeschlagen (Notion-Status='Image Failed'): {e}", file=sys.stderr)
    else:
        print("\nSchritt 6: Kein Bild-Prompt — ueberspringe Bildgenerierung.")

    # Schritt 7: NUR Winner in Notion speichern (fertig mit Draft + Bild)
    target_status = "Image Failed" if image_failed else "Ready to Review"
    print(f"\nSchritt 7: Winner in Notion speichern ({target_status}) ...")
    try:
        page_id = create_post_entry(
            influencer=winner["influencer"],
            post_url=winner["post_url"],
            post_text=winner["post_text"],
            post_date=winner["date"],
            status="New",
        )
        update_with_draft(
            page_id=page_id,
            linkedin_draft=linkedin_draft,
            en_draft=en_draft,
            image_prompt=gen_prompt,
            image_url=image_url,
            title=winner.get("post_excerpt", "")[:60],
            influencer=winner["influencer"],
            image_failed=image_failed,
            image_error=image_error,
            infographic_skeleton=infographic_skeleton,
            post_format=post_format,
            infographic_type=infographic_type,
            archetype=gen_archetype,
        )
        print(f"  Done: {winner['influencer']} -> {target_status}")
    except Exception as e:
        print(f"  FEHLER beim Notion-Speichern: {e}", file=sys.stderr)
        sys.exit(1)

    duration = (datetime.now(timezone.utc) - start_time).seconds
    print(f"\n=== DONE ===")
    print(f"Winner: {winner['influencer']} (Score: {winner['score']}/60)")
    print(f"Dauer: {duration}s")


def main(now=None):
    run_daily()
    weekday = (now or datetime.now(timezone.utc)).weekday()
    if weekday == 3 and _cfg.FEATURES.get("keyword_scrape"):  # Thursday, UTC: keyword scrape feeds Friday's 7-day clustering window
        print("\n=== Donnerstag: starte Keyword-Scrape ===")
        try:
            scrape_and_persist(max_posts=15, posted_limit="week", min_virality=4)
        except Exception as e:
            print(f"  Keyword-Scrape fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if weekday == 4 and _cfg.FEATURES.get("topic_mining"):  # Friday, UTC
        print("\n=== Freitag: starte Blog-Topic-Mining ===")
        try:
            run_topic_mining()
        except Exception as e:
            print(f"  Topic-Mining fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
