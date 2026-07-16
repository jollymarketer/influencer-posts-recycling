"""
Lisocon Slate-Modus (spec docs/superpowers/specs/2026-07-16-lisocon-topic-slate-pool-design.md).

Drei Phasen pro Cron-Lauf (Mo-Fr 07:00 UTC):
  A (immer):  Status=Approved ohne Bild -> Bild generieren
  B (immer):  Status=Topic Approved -> Draft schreiben -> Ready to Review
  C (Mo+Do):  Scrape -> Pool -> Re-Score -> 10er-Slate nach Notion

Nur aktiv bei FEATURES["slate_mode"] (lisocon). Jolly: run_research.run_daily.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

from tools.notion_db import (
    get_existing_post_urls,
    get_recent_linkedin_drafts,
    get_recent_boxes,
    get_pages_by_status,
    create_slate_entry,
    archive_page,
)
from tools.topic_pool import (
    upsert_candidates,
    get_pool_urls,
    get_candidates,
    set_state,
    unslate_and_strike,
    retire_aged,
    get_meta,
    set_meta,
)
from tools.post_scorer import score_posts
from tools.content_matrix import pick_target_box
from tools.linkedin_scraper import scrape_new_posts
from tools.linkedin_keyword_scraper import scrape_keyword_posts
from tools.substack_scraper import scrape_substack_posts

# Gleicher Score-Gate wie run_research.MIN_SCORE (dort nicht importierbar
# ohne den kompletten Daily-Import-Block zu ziehen).
MIN_SCORE = 25


def select_slate(scored: list, cfg) -> list:
    """Pure Slate-Auswahl: pro Persona-Seite Top-N ueber MIN_SCORE,
    knappe Seite wird von der anderen aufgefuellt (fill_marker=True)."""
    slate_cfg = cfg.SLATE
    per, size = slate_cfg["per_persona"], slate_cfg["size"]
    eligible = sorted((c for c in scored if c.get("score", 0) >= MIN_SCORE),
                      key=lambda c: c["score"], reverse=True)
    sides = {"kaeufer": [], "anwender": []}
    for cand in eligible:
        side = sides.get(cand.get("persona", ""))
        if side is not None and len(side) < per:
            side.append(cand)
    slate = sides["kaeufer"] + sides["anwender"]
    chosen = {c["post_url"] for c in slate}
    for cand in eligible:
        if len(slate) >= size:
            break
        if cand["post_url"] not in chosen:
            slate.append({**cand, "fill_marker": True})
            chosen.add(cand["post_url"])
    return slate[:size]


def scrape_all_sources(cfg, existing_urls: set) -> list:
    """Alle drei Quellen, jede non-fatal (gleiches Muster wie run_daily Schritt 2)."""
    posts = []
    try:
        posts.extend(scrape_new_posts(existing_urls=existing_urls))
    except Exception as e:
        print(f"  FEHLER - LinkedIn-Scraping: {e}", file=sys.stderr)
    try:
        posts.extend(scrape_substack_posts(existing_urls=existing_urls))
    except Exception as e:
        print(f"  FEHLER - Substack-Scraping: {e}", file=sys.stderr)
    if cfg.FEATURES.get("keyword_source_daily"):
        kw = cfg.DAILY_KEYWORD_SEARCH
        try:
            seen = set(existing_urls) | {p["post_url"] for p in posts}
            posts.extend(scrape_keyword_posts(
                kw["keywords"], existing_urls=seen,
                max_posts=kw.get("max_posts", 10),
                posted_limit=kw.get("posted_limit", "week")))
        except Exception as e:
            print(f"  FEHLER - Keyword-Scraping: {e}", file=sys.stderr)
    return posts


def _post_to_pool_row(post: dict, client: str) -> dict | None:
    url = post.get("post_url")
    if not url:
        return None
    eng = post.get("engagement", {}) or {}
    date_raw = post.get("date", "")
    return {
        "post_url": url,
        "client": client,
        "source": post.get("source", "linkedin"),
        "influencer": post.get("influencer", ""),
        "post_text": post.get("post_text", ""),
        "post_date": date_raw[:10] if date_raw else None,
        "likes": int(eng.get("likes", 0) or 0),
        "comments": int(eng.get("comments", 0) or 0),
        "shares": int(eng.get("shares", 0) or 0),
        "state": "pool",
    }


def _pool_row_to_post(row: dict) -> dict:
    return {
        "post_url": row["post_url"],
        "influencer": row.get("influencer", ""),
        "post_text": row.get("post_text", ""),
        "date": row.get("post_date") or "",
        "post_excerpt": (row.get("post_text", "") or "")[:300],
        "engagement": {"likes": row.get("likes", 0),
                       "comments": row.get("comments", 0),
                       "shares": row.get("shares", 0)},
    }


def phase_slate(cfg, now) -> None:
    slate_cfg = cfg.SLATE
    meta_key = f"last_slate_at_{cfg.NAME}"
    today = now.date().isoformat()
    print(f"\nPhase C: Slate-Bau ({today}) ...")

    try:
        if get_meta(meta_key) == today:
            print("  Slate heute schon gebaut (Deploy-Re-Run) - Skip.")
            return
    except Exception as e:
        print(f"  FEHLER - Meta-Guard nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return

    try:
        prev = get_pages_by_status("Themenvorschlag")
        for row in prev:
            archive_page(row["page_id"])
        unslate_and_strike([r["post_url"] for r in prev if r["post_url"]],
                           slate_cfg["max_times_slated"])
        retired = retire_aged(cfg.NAME, slate_cfg["max_age_days"])
        if retired:
            print(f"  {retired} Kandidat(en) altersbedingt retired.")
    except Exception as e:
        print(f"  FEHLER - Pool/Archiv nicht erreichbar, Abbruch (kein Slate ohne Pool): {e}",
              file=sys.stderr)
        return

    existing = set()
    try:
        existing = get_existing_post_urls()
    except Exception as e:
        print(f"  FEHLER - Notion-Dedup nicht lesbar: {e}", file=sys.stderr)
    try:
        existing |= get_pool_urls(cfg.NAME)
    except Exception as e:
        print(f"  FEHLER - Pool-Dedup nicht lesbar, Abbruch: {e}", file=sys.stderr)
        return

    new_posts = scrape_all_sources(cfg, existing)
    print(f"  Scrape: {len(new_posts)} neue Posts")
    rows = [r for r in (_post_to_pool_row(p, cfg.NAME) for p in new_posts) if r]
    try:
        upsert_candidates(rows)
        pool_rows = get_candidates(cfg.NAME, ["pool"])
    except Exception as e:
        print(f"  FEHLER - Pool nicht erreichbar, Abbruch (kein Slate ohne Pool): {e}",
              file=sys.stderr)
        return
    print(f"  Aktiver Pool: {len(pool_rows)} Kandidaten")
    if not pool_rows:
        print("  Leerer Pool - kein Slate.")
        return

    try:
        recent_drafts = get_recent_linkedin_drafts(7)
    except Exception:
        recent_drafts = []
    scored = score_posts([_pool_row_to_post(r) for r in pool_rows],
                         recent_drafts=recent_drafts, classify=True)

    slate = select_slate(scored, cfg)
    if not slate:
        print(f"  Kein Kandidat ueber Mindest-Score {MIN_SCORE} - kein Slate.")
        return

    target_box = None
    try:
        target_box = pick_target_box(get_recent_boxes(), cfg)
    except Exception as e:
        print(f"  Matrix-Coverage nicht lesbar (nicht kritisch): {e}", file=sys.stderr)

    written = []
    for cand in slate:
        prio = bool(target_box) and (cand.get("matrix_job", ""),
                                     cand.get("matrix_stage", "")) == target_box
        try:
            create_slate_entry(cand, prio)
            written.append(cand["post_url"])
        except Exception as e:
            print(f"  FEHLER - Slate-Zeile {cand['post_url']}: {e}", file=sys.stderr)

    now_iso = now.isoformat()
    try:
        upsert_candidates([{
            "post_url": c["post_url"], "client": cfg.NAME,
            "persona": c.get("persona", ""), "voc_hit": c.get("voc_hit", ""),
            "topic_angle_de": c.get("topic_angle_de", ""),
            "matrix_job": c.get("matrix_job", ""),
            "matrix_stage": c.get("matrix_stage", ""),
            "score_total": int(c.get("score", 0)),
            "scores": c.get("score_details", {}),
            "reasoning": c.get("reasoning", ""),
            "last_scored_at": now_iso,
        } for c in scored])
        set_state(written, "slated", {"last_slated_at": now_iso})
        set_meta(meta_key, today)
    except Exception as e:
        print(f"  FEHLER - Pool-Writeback: {e}", file=sys.stderr)
    print(f"  Slate geschrieben: {len(written)}/{len(slate)} Zeilen.")
