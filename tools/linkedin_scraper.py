"""
LinkedIn Post Scraper via Apify
Actor: harvestapi/linkedin-profile-posts
- Scrapt Posts der letzten Woche
- Filtert auf Posts, die 1-5 Tage alt sind (Engagement hat Zeit zu akkumulieren)
- Extrahiert Engagement-Metriken fuer Viralitaets-Scoring
"""

import csv
import os
import sys
from datetime import datetime, timezone, timedelta

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
INFLUENCERS_CSV = os.path.join(os.path.dirname(__file__), "..", "influencers.csv")

# Posts muessen mindestens 1 Tag alt sein (Engagement hat Zeit akkumuliert)
# und maximal 5 Tage alt (noch relevant)
MIN_AGE_HOURS = 24
MAX_AGE_HOURS = 120  # 5 Tage


def load_influencers():
    influencers = []
    with open(INFLUENCERS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            influencers.append({
                "name": row["Name"].strip(),
                "linkedin_url": row["LinkedIn URL"].strip(),
            })
    return influencers


def scrape_posts_for_profile(client, profile_url, max_posts=10):
    run_input = {
        "targetUrls": [profile_url],
        "maxPosts": max_posts,
        "postedLimit": "week",
        "includeQuotePosts": True,
        "includeReposts": False,
        "scrapeReactions": False,
        "scrapeComments": False,
    }
    run = client.actor("harvestapi/linkedin-profile-posts").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    return items


def parse_post_age_hours(posted_at) -> float | None:
    """Gibt das Alter des Posts in Stunden zurueck. None wenn nicht parsbar."""
    if not posted_at:
        return None
    try:
        if isinstance(posted_at, dict):
            # Millisekunden-Timestamp
            if "timestamp" in posted_at:
                ts_ms = posted_at["timestamp"]
                post_dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
            elif "date" in posted_at:
                post_dt = datetime.fromisoformat(posted_at["date"].replace("Z", "+00:00"))
            else:
                return None
        elif isinstance(posted_at, str):
            post_dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        else:
            return None
        now = datetime.now(timezone.utc)
        age_hours = (now - post_dt).total_seconds() / 3600
        return age_hours
    except Exception:
        return None


def extract_engagement(item) -> dict:
    """Extrahiert Engagement-Metriken aus dem Apify-Response-Item."""
    eng = item.get("engagement", {})
    if isinstance(eng, dict):
        return {
            "likes": eng.get("likes", 0) or 0,
            "comments": eng.get("comments", 0) or 0,
            "shares": eng.get("shares", 0) or 0,
        }
    return {"likes": 0, "comments": 0, "shares": 0}


def extract_post_data(item, influencer_name):
    post_url = item.get("linkedinUrl", "")
    post_text = item.get("content", "")
    posted_at = item.get("postedAt", "")

    if not post_url or not post_text:
        return None

    # Alter berechnen
    age_hours = parse_post_age_hours(posted_at)

    # Datum fuer Notion
    if isinstance(posted_at, dict):
        date_str = posted_at.get("date", datetime.now(timezone.utc).isoformat())
    else:
        date_str = str(posted_at) if posted_at else datetime.now(timezone.utc).isoformat()

    engagement = extract_engagement(item)

    return {
        "influencer": influencer_name,
        "post_url": post_url,
        "post_text": post_text,
        "post_excerpt": post_text[:300],
        "date": date_str,
        "age_hours": age_hours,
        "engagement": engagement,
    }


def scrape_new_posts(existing_urls: set) -> list:
    """
    Scrapt neue Posts fuer alle Influencer.
    Filtert auf Posts die 1-5 Tage alt sind (optimale Viralitaets-Messung).
    existing_urls: Set von Post-URLs die bereits in Notion vorhanden sind.
    """
    if not APIFY_API_KEY:
        raise ValueError("APIFY_API_KEY fehlt in .env")

    client = ApifyClient(APIFY_API_KEY)
    influencers = load_influencers()
    new_posts = []

    for influencer in influencers:
        if not influencer["linkedin_url"]:
            continue
        print(f"  Scraping: {influencer['name']} ...", flush=True)
        try:
            items = scrape_posts_for_profile(client, influencer["linkedin_url"])
            for item in items:
                post = extract_post_data(item, influencer["name"])
                if not post:
                    continue
                if post["post_url"] in existing_urls:
                    continue

                # Altersfilter: nur Posts aus dem 1-5-Tage-Fenster
                age = post.get("age_hours")
                if age is not None and not (MIN_AGE_HOURS <= age <= MAX_AGE_HOURS):
                    continue

                new_posts.append(post)
                eng = post["engagement"]
                print(
                    f"    OK: {post['post_url'][:70]} "
                    f"| {eng['likes']} Likes, {eng['comments']} Comments"
                )
        except Exception as e:
            print(f"    FEHLER bei {influencer['name']}: {e}", file=sys.stderr)
            continue

    return new_posts


if __name__ == "__main__":
    posts = scrape_new_posts(existing_urls=set())
    print(f"\nGesamt neue Posts: {len(posts)}")
    for p in posts:
        eng = p.get("engagement", {})
        print(f"  [{p.get('age_hours', '?'):.0f}h alt | {eng.get('likes', 0)} Likes] "
              f"{p['influencer']}: {p['post_excerpt'][:60]}...")
