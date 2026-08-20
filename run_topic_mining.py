"""Weekly blog-topic mining: read last 7 days of scraped posts from Supabase,
cluster into themes via Claude, write the top candidates to the Topic-Ideas
Notion DB. Run standalone or triggered from run_research.py on Fridays.

Seit 20.08.2026 (Richard) zwei Erweiterungen:
1. Scoring-Gate (FEATURES["mining_score_gate"]): jeder Post laeuft vor dem
   Clustern durch score_posts; unter MIN_SCORE faellt er raus. Damit praegen
   Vendor-Marketing und ICP-fremde Posts keine Themen mehr.
2. Achsen-Split: hat der Mandant KEYWORDS_BY_AXIS, wird je Achse getrennt
   geclustert (Herkunft source="linkedin_search:<achse>") und die Achse in die
   Themen-DB geschrieben. Der Lauf vom 19.08. clusterte alles in einem Topf,
   10 von 15 Themen wurden Liquiditaet.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.supabase_db import get_posts_since
from tools.topic_clusterer import cluster_topics, filter_candidates
from tools.topic_decisions_db import get_taste_corpus
from tools.topic_ideas_db import get_recent_idea_titles, write_candidates

WINDOW_DAYS = 7
# 2026-07-12 (Richard): mehr Auswahl in der Pick-Queue, Top-5 -> Top-10.
# 2026-08-20 (Richard): Blog Score entfernt. Die Schwelle zaehlt jetzt
# Fundstellen, also wie viele Posts ein Thema wirklich stuetzen.
MIN_SUPPORT = 2
TOP_N = 10
# Deckel je Achse im Achsen-Split (5 Achsen x 3 = max 15 Kandidaten je Lauf).
TOP_N_PER_AXIS = 3

_AXIS_SOURCE_PREFIX = "linkedin_search:"


def _row_to_post(row: dict) -> dict:
    """Supabase-Zeile (flaches likes/comments/shares) -> Post-Dict mit
    engagement-Nest, wie score_posts es erwartet."""
    return {
        **row,
        "engagement": {"likes": row.get("likes", 0) or 0,
                       "comments": row.get("comments", 0) or 0,
                       "shares": row.get("shares", 0) or 0},
    }


def _apply_score_gate(posts: list[dict], cfg) -> list[dict]:
    """Scoring-Gate: unter MIN_SCORE faellt ein Post raus, bevor er Themen
    praegen kann. Ohne Feature-Flag ein No-Op (Jolly-Verhalten unveraendert)."""
    if not cfg.FEATURES.get("mining_score_gate"):
        return posts
    from tools.post_scorer import score_posts  # lazy: baut Prompts beim Import
    floor = int(getattr(cfg, "MIN_SCORE", 0) or 0)
    scored = score_posts([_row_to_post(p) for p in posts])
    kept = [p for p in scored if p.get("score", 0) >= floor]
    print(f"  Scoring-Gate: {len(kept)} von {len(scored)} Posts >= {floor}.")
    return kept


def _split_by_axis(posts: list[dict], cfg) -> dict:
    """Posts nach Achsen-Herkunft gruppieren (source="linkedin_search:<achse>").
    Ohne KEYWORDS_BY_AXIS ein Topf unter dem Schluessel None; unbekannte
    Achsen und andere Quellen landen ebenfalls unter None."""
    axes = getattr(cfg, "KEYWORDS_BY_AXIS", None)
    if not axes:
        return {None: posts}
    groups: dict = {}
    for p in posts:
        src = p.get("source", "") or ""
        axis = src[len(_AXIS_SOURCE_PREFIX):] if src.startswith(_AXIS_SOURCE_PREFIX) else None
        if axis not in axes:
            axis = None
        groups.setdefault(axis, []).append(p)
    return groups


def run_topic_mining(window_days: int = WINDOW_DAYS, top_n: int = TOP_N,
                     cfg=None) -> None:
    cfg = cfg or load_client()
    print("=== Blog Topic Mining ===")
    posts = get_posts_since(window_days)
    print(f"  {len(posts)} Posts im {window_days}-Tage-Fenster.")
    if len(posts) < 2:
        print("  Zu wenige Posts (<2). Skip.")
        return
    posts = _apply_score_gate(posts, cfg)
    if len(posts) < 2:
        print("  Zu wenige Posts nach Scoring-Gate (<2). Skip.")
        return
    # 60 statt 30: bei Top-10/Woche entspricht das weiter ~6 Wochen Dedup-Horizont.
    recent_titles = get_recent_idea_titles(limit=60)
    # Taste-Loop: Richards echte Picks/Rejects als Few-Shot. Non-fatal — ohne
    # Korpus laeuft das Mining wie bisher.
    try:
        taste = get_taste_corpus()
        if taste:
            print(f"  Taste-Korpus: {len(taste['picked'])} picked / {len(taste['rejected'])} rejected.")
    except Exception as e:
        print(f"  Taste-Korpus nicht ladbar (nicht kritisch): {e}")
        taste = None

    groups = _split_by_axis(posts, cfg)
    per_axis = list(groups) != [None]
    for axis, group in groups.items():
        label = axis or ("ohne Achse" if per_axis else "alle")
        if len(group) < 2:
            print(f"  [{label}] zu wenige Posts ({len(group)}). Skip.")
            continue
        candidates = cluster_topics(group, recent_titles=recent_titles,
                                    taste=taste, cfg=cfg)
        print(f"  [{label}] Claude lieferte {len(candidates)} Kandidaten aus {len(group)} Posts.")
        cap = TOP_N_PER_AXIS if per_axis else top_n
        top = filter_candidates(
            candidates, threshold=MIN_SUPPORT, top_n=cap, recent_titles=recent_titles
        )
        print(f"  [{label}] {len(top)} nach Filter (>= {MIN_SUPPORT} Fundstellen, Top-{cap}).")
        n = write_candidates(top, achse=axis)
        print(f"  [{label}] {n} Themen-Kandidaten in Notion geschrieben.")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=WINDOW_DAYS,
                    help=f"clustering window in days (default {WINDOW_DAYS}; use wider for a seed run)")
    ap.add_argument("--top-n", type=int, default=TOP_N,
                    help=f"max candidates written (default {TOP_N}; raise for a long-tail seed)")
    args = ap.parse_args()
    run_topic_mining(window_days=args.days, top_n=args.top_n)
