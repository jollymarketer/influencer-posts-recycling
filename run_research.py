"""
Influencer Posts Recycling — Vollautomatischer Daily Pipeline
Railway Cron: Di-Fr 07:00 UTC (Mo skip — Sonntag-Posts sind GTM-mäßig schwach.
Fr-Cron-Output sitzt das Wochenende in Notion und wird Mo publiziert.)

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

from tools.notion_db import (
    get_existing_post_urls,
    get_recent_linkedin_drafts,
    get_recent_formats,
    create_post_entry,
    update_with_draft,
)
from tools.linkedin_scraper import scrape_new_posts
from tools.substack_scraper import scrape_substack_posts
from tools.post_scorer import score_posts, generate_post_and_image_prompt, build_infographic_prompt, pick_format
from tools.kieai_image import generate_image
from tools.supabase_db import upsert_posts
from run_topic_mining import run_topic_mining

MIN_SCORE = 25


def persist_scraped_posts(linkedin_posts: list, substack_posts: list) -> None:
    """Upsert ALL scraped posts (winners + losers) to Supabase. Non-fatal:
    a failure here must never block the daily winner/draft flow."""
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
    print(f"=== Influencer Posts Recycling - Daily Run ===")
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

    # Schritt 5: LinkedIn-Draft + Bild-Prompt generieren
    print("\nSchritt 5: Generiere LinkedIn-Draft + Bild-Prompt ...")
    try:
        linkedin_draft, en_draft, image_prompt, infographic_skeleton = generate_post_and_image_prompt(winner, post_format)
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

    # Schritt 6: Bild generieren — Infografik aus dem Skelett (Pierre-Rubel-Playbook:
    # Infografik treibt Saves, nicht der Editorial-Poster). Faellt auf den
    # Editorial-Poster zurueck, falls kein Infografik-Skelett vorhanden ist.
    infographic_prompt = build_infographic_prompt(infographic_skeleton, language="English")
    if infographic_prompt:
        gen_prompt, gen_ratio, gen_strip, gen_label = infographic_prompt, "1:1", False, "Infografik"
    else:
        gen_prompt, gen_ratio, gen_strip, gen_label = image_prompt, "3:2", True, "Editorial-Poster"

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
        )
        print(f"  Done: {winner['influencer']} -> {target_status}")
    except Exception as e:
        print(f"  FEHLER beim Notion-Speichern: {e}", file=sys.stderr)
        sys.exit(1)

    duration = (datetime.now(timezone.utc) - start_time).seconds
    print(f"\n=== DONE ===")
    print(f"Winner: {winner['influencer']} (Score: {winner['score']}/60)")
    print(f"Dauer: {duration}s")


def main():
    run_daily()
    if datetime.now(timezone.utc).weekday() == 4:  # Friday, UTC
        print("\n=== Freitag: starte Blog-Topic-Mining ===")
        try:
            run_topic_mining()
        except Exception as e:
            print(f"  Topic-Mining fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
