"""
Keyword-based LinkedIn post scraper via Apify.
Actor: harvestapi/linkedin-post-search

Searches LinkedIn posts by keyword (the locked Jolly target keywords) and returns posts in the same
dict shape as tools/linkedin_scraper, so they feed straight into supabase_db.upsert_posts and the
weekly topic clustering. Source tag for these posts is "linkedin_search".

Unlike the daily profile scraper, there is NO 6-36h viral-window age filter here: keyword mining
wants topical breadth, not freshly-viral posts. Recency is bounded by the actor's postedLimit.
"""
import math
import os
import sys

from tools.apify_auth import apify_client
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Token und Kontowache pro Mandant, siehe tools/apify_auth.py
ACTOR_ID = "harvestapi/linkedin-post-search"
MIN_WORDS = 50


def build_run_input(keywords, max_posts=20, posted_limit="month", sort_by="relevance",
                    author_keywords=""):
    """Build the Apify run input for harvestapi/linkedin-post-search.

    max_posts is per search query. Reactions/comments are off (cost + not needed for mining).
    author_keywords (string): if set, the actor only returns posts whose author headline/job-title
    contains at least one of these terms — cuts off-industry authors server-side (less noise + cost).
    """
    run_input = {
        "searchQueries": list(keywords),
        "maxPosts": max_posts,
        "postedLimit": posted_limit,
        "sortBy": sort_by,
        "contentType": "all",
        "scrapeReactions": False,
        "scrapeComments": False,
    }
    if author_keywords:
        run_input["authorKeywords"] = author_keywords
    return run_input


# High-precision hiring/recruiting markers. These posts go viral but are useless as blog topics.
# Kept tight to avoid false positives on thought-leadership (e.g. bare "looking for" is excluded).
HIRING_MARKERS = (
    "we're hiring", "we are hiring", "now hiring", "#hiring", "hiring for",
    "looking to hire", "join our team", "join the team", "growing our team",
    "growing the team", "building the team", "open role", "open roles",
    "open position", "open positions", "apply now", "job opening", "career opportunity",
    "now accepting applications", "we're recruiting",
    "m/w/d", "m/f/d", "w/m/d", "f/m/d",
    "wir stellen ein", "wir suchen", "stellenangebot", "jetzt bewerben", "werde teil",
)


def is_hiring_ad(text: str) -> bool:
    """True if the post text looks like a job/recruiting ad."""
    low = (text or "").lower()
    return any(marker in low for marker in HIRING_MARKERS)


def virality_score(engagement: dict) -> int:
    """0-10 log-scaled engagement score. Mirrors post_scorer.calculate_virality_score
    (likes + comments*3 + shares*5) so the keyword path is consistent with the daily scorer.
    Inlined to keep this scraper free of the heavy post_scorer import."""
    likes = engagement.get("likes", 0) or 0
    comments = engagement.get("comments", 0) or 0
    shares = engagement.get("shares", 0) or 0
    total = likes + (comments * 3) + (shares * 5)
    return min(10, int(math.log10(total + 1) / math.log10(1001) * 10))


def _author_name(item) -> str:
    author = item.get("author")
    if isinstance(author, dict):
        name = author.get("name") or author.get("fullName") or ""
        if name:
            return name
    return item.get("authorFullName") or item.get("authorName") or ""


def _clean_profile_url(url: str) -> str:
    """Tracking-Parameter und /posts-Suffix entfernen.

    Der Actor liefert URLs wie ".../in/max?miniProfileUrn=urn%3Ali%3A..." und
    ".../company/x/posts". Beides gehoert nicht in influencers.csv: der Query
    veraltet, und /posts ist eine Unterseite, kein Profil (Livelauf 19.08.2026).
    """
    url = (url or "").split("?")[0].split("#")[0].rstrip("/")
    if url.endswith("/posts"):
        url = url[: -len("/posts")]
    return url


def _author_url(item) -> str:
    """Profil-URL des Autors, bevorzugt kanonisch aus publicIdentifier gebaut."""
    author = item.get("author")
    if isinstance(author, dict):
        slug = str(author.get("publicIdentifier") or "").strip()
        typ = str(author.get("type") or "").strip().lower()
        if slug:
            teil = "company" if typ == "company" else "in"
            return f"https://www.linkedin.com/{teil}/{slug}"
        for key in ("linkedinUrl", "url", "profileUrl", "publicProfileUrl", "link"):
            val = author.get(key)
            if val:
                return _clean_profile_url(str(val))
    for key in ("authorProfileUrl", "authorUrl", "authorLinkedinUrl"):
        val = item.get(key)
        if val:
            return _clean_profile_url(str(val))
    return ""


def _author_headline(item) -> str:
    """Positionszeile des Autors. Der Actor nennt das Feld `info`, nicht
    `headline` - im Livelauf 19.08.2026 verifiziert."""
    author = item.get("author")
    if isinstance(author, dict):
        for key in ("info", "headline", "occupation", "subtitle", "position"):
            val = author.get(key)
            if val:
                return str(val)
    return str(item.get("authorHeadline") or "")


def _author_type(item) -> str:
    """`profile` oder `company`. Fuer die Stimmen-Suche zaehlen Personen."""
    author = item.get("author")
    if isinstance(author, dict):
        return str(author.get("type") or "").strip().lower()
    return ""


def _post_date(posted_at) -> str:
    if isinstance(posted_at, dict):
        return posted_at.get("date", "")
    return str(posted_at) if posted_at else ""


def extract_keyword_post(item) -> dict | None:
    """Parse one Apify post item into the shared post dict, or None if unusable."""
    post_url = item.get("linkedinUrl", "")
    post_text = item.get("content", "")
    if not post_url or not post_text:
        return None
    if len(post_text.split()) < MIN_WORDS:
        return None

    eng = item.get("engagement", {})
    engagement = {
        "likes": (eng.get("likes", 0) or 0) if isinstance(eng, dict) else 0,
        "comments": (eng.get("comments", 0) or 0) if isinstance(eng, dict) else 0,
        "shares": (eng.get("shares", 0) or 0) if isinstance(eng, dict) else 0,
    }
    return {
        "influencer": _author_name(item),
        "author_url": _author_url(item),
        "author_headline": _author_headline(item),
        "author_type": _author_type(item),
        "post_url": post_url,
        "post_text": post_text,
        "post_excerpt": post_text[:300],
        "date": _post_date(item.get("postedAt", "")),
        "engagement": engagement,
        "virality": virality_score(engagement),
    }


def scrape_keyword_posts(
    keywords,
    existing_urls=None,
    max_posts=20,
    posted_limit="month",
    sort_by="relevance",
    min_virality=0,
    author_keywords="",
    exclude_hiring=True,
    client=None,
) -> list:
    """Scrape posts for the given keyword queries. Dedups within the run and against existing_urls.

    min_virality (0-10): drop posts whose virality score is below this floor. The actor has no
    engagement input filter, so this is applied post-scrape (Apify still charges for every scraped
    post; the filter only controls what is kept/persisted).
    author_keywords (string): server-side author-headline filter (see build_run_input).
    exclude_hiring (bool): drop job/recruiting ads (viral but useless as blog topics).
    """
    existing = existing_urls or set()
    if client is None:
        client = apify_client()

    run_input = build_run_input(keywords, max_posts, posted_limit, sort_by, author_keywords)
    run = client.actor(ACTOR_ID).call(run_input=run_input)
    if run is None:
        return []
    items = client.dataset(run.default_dataset_id).iterate_items()

    posts = []
    seen = set(existing)
    for item in items:
        post = extract_keyword_post(item)
        if not post:
            continue
        if post["post_url"] in seen:
            continue
        if post["virality"] < min_virality:
            continue
        if exclude_hiring and is_hiring_ad(post["post_text"]):
            continue
        seen.add(post["post_url"])
        posts.append(post)
    return posts


if __name__ == "__main__":
    out = scrape_keyword_posts(["revenue operations"], max_posts=5)
    print(f"Posts: {len(out)}")
    for p in out:
        print(f"  {p['influencer']}: {p['post_excerpt'][:60]}...")
