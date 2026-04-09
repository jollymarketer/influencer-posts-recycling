"""
Influencer Posts Recycling — Vollautomatischer Daily Pipeline
Railway Cron: taeglich 07:00 UTC

Flow:
1. Bestehende Post-URLs aus Notion laden (Duplikat-Filter)
2. Neue Posts scrapen (LinkedIn + Substack)
3. Posts in Notion schreiben (Status: "New")
4. Posts scoren (KI + Engagement)
5. Winner waehlen (Mindest-Score: 25/60)
6. DACH-LinkedIn-Draft + Bild-Prompt generieren
7. Bild generieren (kie.ai)
8. Notion-Eintrag updaten (Status: "Ready to Review")
9. Restliche Posts auf "Skipped" setzen
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from tools.notion_db import (
    get_existing_post_urls,
    get_recent_linkedin_drafts,
    create_post_entry,
    update_with_draft,
    set_post_status,
)
from tools.linkedin_scraper import scrape_new_posts
from tools.substack_scraper import scrape_substack_posts
from tools.post_scorer import score_posts, generate_post_and_image_prompt
from tools.kieai_image import generate_image

MIN_SCORE = 25


def main():
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

    if not new_posts:
        print("  Keine neuen Posts gefunden. Run beendet.")
        return

    print(f"  Gesamt: {len(new_posts)} neue Inhalte.")

    # Schritt 3: Posts in Notion schreiben (Status: "New")
    print(f"\nSchritt 3: Schreibe {len(new_posts)} Posts in Notion ...")
    posts_with_ids = []
    for post in new_posts:
        try:
            page_id = create_post_entry(
                influencer=post["influencer"],
                post_url=post["post_url"],
                post_text=post["post_text"],
                post_date=post["date"],
                status="New",
            )
            posts_with_ids.append({**post, "page_id": page_id})
            print(f"  OK: {post['influencer']} - {post['post_excerpt'][:50]}...")
        except Exception as e:
            print(f"  FEHLER bei {post['influencer']}: {e}", file=sys.stderr)

    if not posts_with_ids:
        print("  Alle Posts konnten nicht gespeichert werden. Run beendet.")
        return

    # Schritt 4: Scoren (in-memory, Engagement-Daten noch vorhanden)
    print(f"\nSchritt 4: Score {len(posts_with_ids)} Posts ...")
    try:
        recent_drafts = get_recent_linkedin_drafts(7)
        scored = score_posts(posts_with_ids, recent_drafts=recent_drafts)
        for p in scored[:3]:
            print(f"  [{p['score']}/60] {p['influencer']}: {p.get('reasoning', '')[:80]}")
    except Exception as e:
        print(f"  FEHLER beim Scoring: {e}", file=sys.stderr)
        sys.exit(1)

    # Schritt 5: Winner waehlen
    winner = scored[0] if scored and scored[0]["score"] >= MIN_SCORE else None
    if not winner:
        top_score = scored[0]["score"] if scored else 0
        print(f"\n  Kein Post erreicht Mindest-Score {MIN_SCORE}/60 (bester: {top_score}). Run beendet.")
        return

    print(f"\nSchritt 5: Winner = {winner['influencer']} (Score: {winner['score']}/60)")

    # Schritt 6: LinkedIn-Draft + Bild-Prompt generieren
    print("\nSchritt 6: Generiere LinkedIn-Draft + Bild-Prompt ...")
    try:
        linkedin_draft, image_prompt = generate_post_and_image_prompt(winner)
    except Exception as e:
        print(f"  FEHLER bei Content-Generierung: {e}", file=sys.stderr)
        sys.exit(1)

    if not linkedin_draft:
        print("  FEHLER: Leerer LinkedIn-Draft. Kein Notion-Update.", file=sys.stderr)
        sys.exit(1)

    print(f"  Draft: {len(linkedin_draft)} Zeichen")
    print(f"  Bild-Prompt: {'OK' if image_prompt else 'leer'}")

    # Schritt 7: Bild generieren
    image_url = ""
    if image_prompt:
        print("\nSchritt 7: Generiere Bild (kie.ai) ...")
        try:
            image_url = generate_image(image_prompt)
            print(f"  Bild-URL: {image_url}")
        except Exception as e:
            print(f"  Bildgenerierung fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    else:
        print("\nSchritt 7: Kein Bild-Prompt — ueberspringe Bildgenerierung.")

    # Schritt 8: Notion-Eintrag updaten
    print("\nSchritt 8: Notion-Update (Ready to Review) ...")
    try:
        update_with_draft(
            page_id=winner["page_id"],
            linkedin_draft=linkedin_draft,
            image_prompt=image_prompt,
            image_url=image_url,
            title=winner.get("post_excerpt", "")[:60],
            influencer=winner["influencer"],
        )
        print(f"  Done: {winner['influencer']} -> Ready to Review")
    except Exception as e:
        print(f"  FEHLER beim Notion-Update: {e}", file=sys.stderr)
        sys.exit(1)

    # Schritt 9: Restliche Posts auf "Skipped" setzen
    print("\nSchritt 9: Restliche Posts -> Skipped ...")
    skipped = 0
    for post in posts_with_ids:
        if post["page_id"] != winner["page_id"]:
            try:
                set_post_status(post["page_id"], "Skipped")
                skipped += 1
            except Exception as e:
                print(f"  Skip-Fehler bei {post['influencer']}: {e}", file=sys.stderr)
    print(f"  {skipped} Posts auf Skipped gesetzt.")

    duration = (datetime.now(timezone.utc) - start_time).seconds
    print(f"\n=== DONE ===")
    print(f"Winner: {winner['influencer']} (Score: {winner['score']}/60)")
    print(f"Dauer: {duration}s")


if __name__ == "__main__":
    main()
