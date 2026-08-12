"""Einmalige Erstbefuellung: Kommentar-Entwuerfe fuer den SWOT
Content-Redaktionsplan (12.08.2026).

Nutzt den bestehenden Kommentar-Pfad (fetch_fresh_posts, draft_comment,
Robert-Stimme aus clients/swot), schreibt aber JSON statt in die
Engine-Notion-DB: die Eintraege legt die Claude-Session per Notion-MCP in die
Portal-DB (Typ "LinkedIn-Kommentar"), weil die Engine-Integration dort keinen
Zugriff hat. Der regulaere Mo/Mi/Fr-Betrieb folgt mit dem Engine-Umbau.

Abweichung vom Betriebs-Config: max_age_hours 168 statt 72, damit die
Erstbefuellung genug Kandidaten sieht (Messung 10.08.: 7 Quellen liefern in
einer Woche nur ~8 brauchbare Posts). Alter steht je Entwurf im Ergebnis,
Robert pickt die frischen.

Run: CLIENT=swot python scripts/swot_comment_drafts_once.py
Kosten: ein Apify-Run (7 Profile) ~0,01-0,05 USD plus ~5 Sonnet-Calls.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("CLIENT", "swot")

from clients import load_client
from tools.comment_drafts import draft_comment, fetch_fresh_posts
from tools.linkedin_scraper import load_influencers

RESULT_PATH = os.path.join(ROOT, ".tmp", "swot_comments_result.json")

SETTINGS = {
    "max_posts_per_profile": 3,
    "posted_limit": "week",
    "max_age_hours": 168,   # Erstbefuellung, siehe Docstring
}
DRAFTS_TOTAL = 5
POSTER = "Robert"


def main():
    cfg = load_client()
    if cfg.NAME != "swot":
        sys.exit(f"CLIENT={cfg.NAME}, erwartet swot. Abbruch.")

    profiles = [p for p in load_influencers() if p.get("linkedin_url")]
    print(f"{len(profiles)} Quellen geladen.", flush=True)
    posts = fetch_fresh_posts(profiles, SETTINGS)
    print(f"{len(posts)} brauchbare Posts im Fenster.", flush=True)

    results = []
    for post in posts:
        if len(results) >= DRAFTS_TOTAL:
            break
        draft = draft_comment(cfg, post, POSTER)
        if not draft:
            continue
        draft["age_hours"] = round(post.get("age_hours", 0))
        results.append(draft)
        print(f"OK: {draft['influencer'][:40]} ({draft['age_hours']}h alt)", flush=True)

    os.makedirs(os.path.dirname(RESULT_PATH), exist_ok=True)
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n{len(results)} Entwuerfe -> {RESULT_PATH}")


if __name__ == "__main__":
    main()
