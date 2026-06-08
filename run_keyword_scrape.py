"""Keyword-based LinkedIn scrape -> Supabase mining store.

Scrapes LinkedIn posts for Jolly's locked target keywords (the topics jolly wants to rank / be
cited for) and upserts them into blog_content_mining.influencer_posts with source="linkedin_search".
The existing weekly Friday clustering (run_topic_mining.py) then turns them into Topic-Idea
candidates alongside the influencer-profile posts.

Standalone / on-demand. Does NOT touch the daily run_research flow.

    python run_keyword_scrape.py                       # full run, defaults
    python run_keyword_scrape.py --max-posts 10        # cheaper
    python run_keyword_scrape.py --keywords "revops" "cold email"   # subset (verification run)
    python run_keyword_scrape.py --no-write            # scrape only, skip Supabase upsert
"""
import argparse
import sys

from tools.linkedin_keyword_scraper import scrape_keyword_posts
from tools.supabase_db import upsert_posts

# Locked 2026-06-08 with Richard. Derived from the AI-visibility scoreboard gaps + beachheads.
# Commercial pillars + mechanism long-tails + AI/KI-applied-to-GTM. No HubSpot, no cold calling.
KEYWORDS = [
    # Commercial pillars
    "revenue operations",
    "b2b lead generation",
    "go-to-market strategy",
    "cold email",
    "fractional cmo",
    # Mechanism long-tails
    "cold email deliverability",
    "email warmup",
    "buying committee",
    "ideal customer profile",
    "sales forecasting",
    "account based marketing",
    "intent data",
    "demand generation",
    # AI / KI applied to GTM
    "gtm engineering",
    "ai sdr",
    "ai personalization sales",
    "revops automation",
    "answer engine optimization",
]

# Server-side author-headline filter. NOTE: the actor treats authorKeywords as a SINGLE term, not a
# multi-term OR-list (a space/comma list returns 0 results). So this is disabled by default; pass a
# single broad term via --author-keywords (e.g. "sales") if you want it. Off-industry/hiring noise is
# better handled post-scrape (see virality filter + downstream blog_score clusterer).
AUTHOR_KEYWORDS = ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-posts", type=int, default=20, help="max posts per keyword query")
    ap.add_argument("--posted-limit", default="month", help="any|1h|24h|week|month|3months|...")
    ap.add_argument("--min-virality", type=int, default=5,
                    help="0-10 floor; drop posts below this engagement score (default 5)")
    ap.add_argument("--author-keywords", default=AUTHOR_KEYWORDS,
                    help="server-side author-headline filter (comma-separated). '' to disable.")
    ap.add_argument("--keywords", nargs="*", help="override keyword set (verification runs)")
    ap.add_argument("--no-write", action="store_true", help="scrape only, skip Supabase upsert")
    args = ap.parse_args()

    keywords = args.keywords or KEYWORDS
    print(f"Scraping {len(keywords)} keyword queries, max {args.max_posts}/query, "
          f"posted_limit={args.posted_limit}, min_virality={args.min_virality}, "
          f"author_keywords={args.author_keywords!r} ...", flush=True)

    posts = scrape_keyword_posts(
        keywords, max_posts=args.max_posts, posted_limit=args.posted_limit,
        min_virality=args.min_virality, author_keywords=args.author_keywords,
    )
    print(f"  {len(posts)} usable posts (>=50 words, virality>={args.min_virality}, deduped).")

    if args.no_write:
        print("  --no-write: skipping Supabase upsert.")
        for p in sorted(posts, key=lambda x: x["virality"], reverse=True)[:15]:
            eng = p["engagement"]
            print(f"    v{p['virality']} [{eng['likes']}L/{eng['comments']}C/{eng['shares']}S] "
                  f"{p['influencer']}: {p['post_excerpt'][:55]}...")
        return 0

    try:
        n = upsert_posts(posts, source="linkedin_search")
        print(f"  Supabase: {n} posts persisted (source=linkedin_search).")
    except Exception as e:
        print(f"  Supabase-Persist fehlgeschlagen: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
