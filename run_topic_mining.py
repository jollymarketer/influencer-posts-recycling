"""Weekly blog-topic mining: read last 7 days of scraped posts from Supabase,
cluster into themes via Claude, write the top candidates to the Topic-Ideas
Notion DB. Run standalone or triggered from run_research.py on Fridays.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from tools.supabase_db import get_posts_since
from tools.topic_clusterer import cluster_topics, filter_candidates
from tools.topic_ideas_db import get_recent_idea_titles, write_candidates

WINDOW_DAYS = 7
SCORE_THRESHOLD = 70
TOP_N = 5


def run_topic_mining() -> None:
    print("=== Blog Topic Mining ===")
    posts = get_posts_since(WINDOW_DAYS)
    print(f"  {len(posts)} Posts im {WINDOW_DAYS}-Tage-Fenster.")
    if len(posts) < 2:
        print("  Zu wenige Posts (<2). Skip.")
        return
    recent_titles = get_recent_idea_titles(limit=30)
    candidates = cluster_topics(posts, recent_titles=recent_titles)
    print(f"  Claude lieferte {len(candidates)} Roh-Themen.")
    top = filter_candidates(
        candidates, threshold=SCORE_THRESHOLD, top_n=TOP_N, recent_titles=recent_titles
    )
    print(f"  {len(top)} Themen nach Filter (>= {SCORE_THRESHOLD}, Top-{TOP_N}).")
    n = write_candidates(top)
    print(f"  {n} Themen-Kandidaten in Notion geschrieben.")


if __name__ == "__main__":
    run_topic_mining()
