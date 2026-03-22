"""
Influencer Posts Recycling — Vollautomatischer Daily Run
Railway Cron: taeglich 07:00 UTC

Flow:
1. Bestehende Post-URLs aus Notion laden (Duplikat-Filter)
2. Neue Posts scrapen (alle 20 Influencer via Apify)
3. KI-Vetting: Posts nach Fit mit Jolly Marketer bewerben
4. Winner-Post auswaehlen (hoechster Score)
5. LinkedIn-Draft generieren (Claude API)
6. Infografik-Prompt generieren (Claude API)
7. Bild generieren (kie.ai Nano Banana 2 + Polling)
8. Notion-Eintrag erstellen (Status: "Ready to Review")
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from tools.notion_db import get_existing_post_urls, create_post_entry
from tools.linkedin_scraper import scrape_new_posts
from tools.substack_scraper import scrape_substack_posts
from tools.post_scorer import score_posts, generate_post_and_image_prompt
from tools.kieai_image import generate_image


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

    # Schritt 3: KI-Vetting
    print(f"\nSchritt 3: KI-Vetting {len(new_posts)} Posts ...")
    try:
        scored_posts = score_posts(new_posts)
        print(f"  Top 3 nach Score:")
        for i, p in enumerate(scored_posts[:3]):
            d = p.get("score_details", {})
            virality = d.get("viralitaet", 0)
            eng = p.get("engagement", {})
            print(f"    #{i+1} [{p['score']}/50] {p['influencer']}: {p['post_excerpt'][:60]}...")
            print(f"         Viralitaet: {virality}/10 ({eng.get('likes',0)} Likes, {eng.get('comments',0)} Comments)")
            print(f"         Reasoning: {p.get('reasoning', '')}")
    except Exception as e:
        print(f"  FEHLER - Scoring: {e}", file=sys.stderr)
        sys.exit(1)

    # Schritt 4: Winner auswaehlen
    winner = scored_posts[0]
    source = winner.get("source", "linkedin")
    print(f"\nSchritt 4: Winner = {winner['influencer']} (Score: {winner['score']}/50, Quelle: {source})")
    print(f"  URL: {winner['post_url']}")

    # Schritt 5+6: LinkedIn-Draft (DACH Deutsch) + Bild-Prompt in einem Call
    print("\nSchritt 5+6: Generiere DACH-LinkedIn-Post + Bild-Prompt ...")
    try:
        linkedin_draft, image_prompt = generate_post_and_image_prompt(winner)
        print(f"  LinkedIn-Draft: {len(linkedin_draft)} Zeichen")
        print(f"  Bild-Prompt: {len(image_prompt)} Zeichen")
    except Exception as e:
        print(f"  FEHLER - Content-Generierung: {e}", file=sys.stderr)
        linkedin_draft = ""
        image_prompt = ""

    # Schritt 7: Bild generieren
    image_url = ""
    if image_prompt:
        print("\nSchritt 7: Generiere Bild via kie.ai (Nano Banana 2) ...")
        try:
            image_url = generate_image(image_prompt)
            print(f"  Bild-URL: {image_url}")
        except Exception as e:
            print(f"  FEHLER - Bildgenerierung: {e}", file=sys.stderr)

    # Schritt 8: Notion-Eintrag erstellen
    print("\nSchritt 8: Schreibe in Notion ...")
    try:
        page_id = create_post_entry(
            influencer=winner["influencer"],
            post_url=winner["post_url"],
            post_text=winner["post_text"],
            post_date=winner["date"],
            status="Ready to Review",
            linkedin_draft=linkedin_draft,
            image_prompt=image_prompt,
            image_url=image_url,
        )
        page_url = f"https://www.notion.so/{page_id.replace('-', '')}"
        print(f"  Notion-Eintrag: {page_url}")
    except Exception as e:
        print(f"  FEHLER - Notion: {e}", file=sys.stderr)
        sys.exit(1)

    # Summary
    duration = (datetime.now(timezone.utc) - start_time).seconds
    print(f"\n=== DONE ===")
    eng = winner.get("engagement", {})
    print(f"Winner: {winner['influencer']} (Score: {winner['score']}/50 | {eng.get('likes',0)} Likes)")
    print(f"Notion: https://www.notion.so/{page_id.replace('-', '')}")
    print(f"Status: Ready to Review")
    print(f"Dauer: {duration}s")


if __name__ == "__main__":
    main()
