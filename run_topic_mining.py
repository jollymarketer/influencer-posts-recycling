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
# 2026-07-12 (Richard): mehr Auswahl in der Pick-Queue — Threshold 70->60,
# Top-5 -> Top-10. Clay-Cap (40) bleibt unter dem Threshold wirksam.
SCORE_THRESHOLD = 60
TOP_N = 10


def run_topic_mining(window_days: int = WINDOW_DAYS, top_n: int = TOP_N) -> None:
    print("=== Blog Topic Mining ===")
    posts = get_posts_since(window_days)
    print(f"  {len(posts)} Posts im {window_days}-Tage-Fenster.")
    if len(posts) < 2:
        print("  Zu wenige Posts (<2). Skip.")
        return
    # 60 statt 30: bei Top-10/Woche entspricht das weiter ~6 Wochen Dedup-Horizont.
    recent_titles = get_recent_idea_titles(limit=60)
    candidates = cluster_topics(posts, recent_titles=recent_titles)
    print(f"  Claude lieferte {len(candidates)} Long-Tail-Kandidaten.")
    top = filter_candidates(
        candidates, threshold=SCORE_THRESHOLD, top_n=top_n, recent_titles=recent_titles
    )
    print(f"  {len(top)} nach Filter (>= {SCORE_THRESHOLD}, Top-{top_n}).")
    n = write_candidates(top)
    print(f"  {n} Themen-Kandidaten in Notion geschrieben.")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=WINDOW_DAYS,
                    help=f"clustering window in days (default {WINDOW_DAYS}; use wider for a seed run)")
    ap.add_argument("--top-n", type=int, default=TOP_N,
                    help=f"max candidates written (default {TOP_N}; raise for a long-tail seed)")
    args = ap.parse_args()
    run_topic_mining(window_days=args.days, top_n=args.top_n)
