"""
Substack Article Scraper via RSS Feeds
- Liest RSS-Feeds der Influencer-Substacks
- Filtert auf Artikel die 1-5 Tage alt sind (identisches Fenster wie LinkedIn)
- Gibt Posts im gleichen Format wie linkedin_scraper zurueck
"""

import calendar
import csv
import os
import re
import sys
from datetime import datetime, timezone

import feedparser
from dotenv import load_dotenv

load_dotenv()

INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "..", "influencers.csv")

MIN_AGE_HOURS = 24
MAX_AGE_HOURS = 120  # 5 Tage


def load_influencers_with_substack():
    influencers = []
    with open(INFLUENCERS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            substack_url = row.get("Substack URL", "").strip()
            if substack_url:
                influencers.append({
                    "name": row["Name"].strip(),
                    "substack_url": substack_url,
                })
    return influencers


def fetch_rss_items(feed_url: str) -> list[dict]:
    """Parst einen RSS/Atom-Feed via feedparser und gibt Items als Dicts zurueck."""
    feed = feedparser.parse(feed_url)
    items = []
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()

        # Datum: published_parsed ist ein time.struct_time in UTC
        published = entry.get("published_parsed")

        # Content: bevorzuge content[0].value (Atom), dann summary (RSS)
        full_text = ""
        if entry.get("content"):
            full_text = entry["content"][0].get("value", "")
        if not full_text:
            full_text = entry.get("summary", "")

        items.append({
            "title": title,
            "link": link,
            "published_parsed": published,
            "text": full_text,
        })
    return items


def strip_html(text: str) -> str:
    """Entfernt HTML-Tags fuer sauberen Plaintext."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def scrape_substack_posts(existing_urls: set) -> list:
    """
    Scrapt neue Substack-Artikel fuer alle Influencer mit Substack-URL.
    Gibt Posts im gleichen Format wie linkedin_scraper zurueck.
    """
    influencers = load_influencers_with_substack()
    new_posts = []
    now = datetime.now(timezone.utc)

    for influencer in influencers:
        print(f"  Substack: {influencer['name']} ...", flush=True)
        try:
            items = fetch_rss_items(influencer["substack_url"])
            for item in items:
                link = item["link"]
                if not link or link in existing_urls:
                    continue

                published = item.get("published_parsed")
                if published is None:
                    continue

                # feedparser gibt published_parsed als time.struct_time in UTC zurueck
                pub_ts = calendar.timegm(published)
                pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)

                age_hours = (now - pub_dt).total_seconds() / 3600
                if not (MIN_AGE_HOURS <= age_hours <= MAX_AGE_HOURS):
                    continue

                # Plaintext aus HTML extrahieren
                plain_text = strip_html(item["text"])
                if len(plain_text) < 100:
                    plain_text = item["title"]  # Fallback auf Titel

                # Titel vorne einbauen fuer besseres Scoring
                full_text = f"{item['title']}\n\n{plain_text}" if item["title"] else plain_text

                post = {
                    "influencer": influencer["name"],
                    "post_url": link,
                    "post_text": full_text,
                    "post_excerpt": full_text[:300],
                    "date": pub_dt.isoformat(),
                    "age_hours": age_hours,
                    "engagement": {"likes": 0, "comments": 0, "shares": 0},
                    "source": "substack",
                }
                new_posts.append(post)
                print(f"    OK: {link[:70]} | {age_hours:.0f}h alt")

        except Exception as e:
            print(f"    FEHLER bei {influencer['name']}: {e}", file=sys.stderr)
            continue

    return new_posts


if __name__ == "__main__":
    posts = scrape_substack_posts(existing_urls=set())
    print(f"\nGesamt neue Substack-Artikel: {len(posts)}")
    for p in posts:
        print(f"  [{p['age_hours']:.0f}h alt] {p['influencer']}: {p['post_excerpt'][:60]}...")
