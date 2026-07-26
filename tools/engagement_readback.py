"""Engagement-Readback fuer die eigenen veroeffentlichten Posts.

Die Pipeline endete bisher beim Publish: Likes/Kommentare der EIGENEN Posts
liefen nirgends zurueck, Winner-Repeat entschied rein nach Alter. Dieser Schritt
scrapt die eigenen Profile (ein Apify-Run fuer alle Poster zusammen) und
schreibt die Zahlen in die Notion-Zeile des jeweiligen Posts.

Nur Reichweiten-Proxy: LinkedIn-Impressionen sind ueber die API nicht sichtbar,
die holt sich der Poster aus seinen nativen Analytics.
"""
import os
import re
import sys
from datetime import datetime, timezone

from apify_client import ApifyClient
from dotenv import load_dotenv

from clients import load_client
from tools.notion_db import get_published_rows, update_engagement

load_dotenv()

_cfg = load_client()
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

# LinkedIn-Share-/Activity-IDs sind 19-stellig. Die Notion-Zeile traegt die
# Feed-URL des Make-Publishers (urn:li:share:...), der Scraper liefert
# linkedinUrl/shareUrn - gemeinsamer Nenner ist die nackte ID.
_ID_RE = re.compile(r"\d{15,25}")


def extract_ids(*values) -> set:
    """Alle LinkedIn-Objekt-IDs aus beliebigen URL-/URN-Feldern."""
    ids = set()
    for value in values:
        if isinstance(value, str):
            ids |= set(_ID_RE.findall(value))
    return ids


def match_row(row: dict, items: list) -> dict | None:
    """Scrape-Item zur Notion-Zeile: Treffer ueber gemeinsame Objekt-ID."""
    row_ids = extract_ids(row.get("live_url", ""))
    if not row_ids:
        return None
    for item in items:
        item_ids = extract_ids(item.get("linkedinUrl", ""), item.get("shareUrn", ""),
                               item.get("shareLinkedinUrl", ""), item.get("entityId", ""))
        if row_ids & item_ids:
            return item
    return None


def fetch_own_posts(profiles: list, max_posts: int, posted_limit: str) -> list:
    """Ein Apify-Run fuer alle eigenen Profile (Batch ist billiger als je Profil)."""
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY fehlt in .env")
    urls = [p["url"] for p in profiles if p.get("url")]
    if not urls:
        return []
    client = ApifyClient(APIFY_API_KEY)
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input={
        "targetUrls": urls,
        "maxPosts": max_posts,
        "postedLimit": posted_limit,
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    })
    if run is None:
        return []
    return list(client.dataset(run.default_dataset_id).iterate_items())


def _engagement(item: dict) -> tuple[int, int, int]:
    eng = item.get("engagement", {}) or {}
    return (int(eng.get("likes", 0) or 0),
            int(eng.get("comments", 0) or 0),
            int(eng.get("shares", 0) or 0))


def run_readback(cfg=None) -> dict:
    """Schreibt Likes/Kommentare/Shares in jede veroeffentlichte Notion-Zeile,
    die im Scrape-Fenster liegt. Rueckgabe: Kennzahlen des Laufs."""
    cfg = cfg or _cfg
    settings = getattr(cfg, "ENGAGEMENT_READBACK", None)
    profiles = getattr(cfg, "OWN_PROFILES", None)
    if not settings or not profiles:
        print("  Engagement-Readback nicht konfiguriert - Skip.")
        return {"matched": 0, "rows": 0}

    rows = get_published_rows()
    if not rows:
        print("  Keine veroeffentlichten Zeilen - Skip.")
        return {"matched": 0, "rows": 0}

    items = fetch_own_posts(profiles, settings.get("max_posts_per_profile", 20),
                            settings.get("posted_limit", "month"))
    print(f"  {len(items)} eigene Posts gescrapt, {len(rows)} veroeffentlichte Zeilen.")

    now_iso = datetime.now(timezone.utc).isoformat()
    matched, top = 0, []
    for row in rows:
        item = match_row(row, items)
        if not item:
            continue
        likes, comments, shares = _engagement(item)
        try:
            update_engagement(row["page_id"], likes, comments, shares, now_iso)
        except Exception as e:
            print(f"    FEHLER - Readback {row['page_id']}: {e}", file=sys.stderr)
            continue
        matched += 1
        top.append((likes + 2 * comments + 3 * shares, likes, comments,
                    row.get("poster", ""), row.get("posted_at", "")[:10]))

    top.sort(reverse=True)
    for score, likes, comments, poster, date in top[:3]:
        print(f"    Top: {date} {poster} - {likes} Likes, {comments} Kommentare")
    print(f"  Engagement zurueckgeschrieben: {matched}/{len(rows)} Zeilen.")
    return {"matched": matched, "rows": len(rows)}


if __name__ == "__main__":
    run_readback()
