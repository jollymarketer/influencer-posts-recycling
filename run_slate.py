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
    get_recent_formats,
    get_recent_infographic_types,
    get_recent_archetypes,
    get_recent_assets,
    get_pages_by_status,
    create_slate_entry,
    archive_page,
    update_with_draft,
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
from tools.post_scorer import (
    score_posts,
    generate_post_and_image_prompt,
    pick_format,
    parse_infographic_type,
    normalize_infographic_type,
    persona_block,
    assets_block,
)
from tools.content_matrix import (
    FORMAT_ASSET_ATTR,
    FORMAT_TO_BOX,
    asset_for_format,
    figures_ok,
    formats_for_box,
    free_formats,
    pick_target_box,
)
from tools.image_archetypes import (
    select_archetype,
    build_archetype_prompt,
    skeleton_signals,
)
from tools.image_repair import fill_missing_images
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


def run_slate_mode(cfg, now=None) -> None:
    now = now or datetime.now(timezone.utc)
    print(f"=== Slate-Modus (Client: {cfg.NAME}) — {now.strftime('%Y-%m-%d %H:%M UTC')} ===")
    phase_images(cfg)
    phase_drafts(cfg)
    if now.weekday() in tuple(cfg.SLATE.get("days", (0, 3))):
        phase_slate(cfg, now)
    else:
        print(f"\nKein Slate-Tag (weekday {now.weekday()}).")


def phase_images(cfg) -> None:
    print("\nPhase A: Bilder fuer freigegebene Texte ...")
    try:
        n = fill_missing_images()
        print(f"  {n} Bild(er) generiert.")
    except Exception as e:
        print(f"  FEHLER - Phase A: {e}", file=sys.stderr)


def _persona_by_id(cfg, persona_id: str) -> dict | None:
    personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
    hit = next((p for p in personas if p.get("id") == persona_id), None)
    if hit:
        return hit
    return next((p for p in personas if p.get("share") == "dominant"), None)


def phase_drafts(cfg) -> None:
    print("\nPhase B: Drafts fuer gepickte Themen ...")
    try:
        picked = get_pages_by_status("Topic Approved")
    except Exception as e:
        print(f"  FEHLER - Notion nicht lesbar: {e}", file=sys.stderr)
        return
    if not picked:
        print("  Keine Picks.")
        return
    try:
        pool = {r["post_url"]: r
                for r in get_candidates(cfg.NAME, ["slated", "picked", "pool"])}
    except Exception as e:
        print(f"  FEHLER - Pool nicht lesbar: {e}", file=sys.stderr)
        return

    for page in picked:
        try:
            _draft_one(cfg, page, pool)
        except Exception as e:
            print(f"  FEHLER - Draft fuer {page['post_url']}: {e}", file=sys.stderr)


def _draft_one(cfg, page: dict, pool: dict) -> None:
    row = pool.get(page["post_url"])
    if not row:
        print(f"  Kein Pool-Kandidat fuer {page['post_url']} - Skip.", file=sys.stderr)
        return
    winner = _pool_row_to_post(row)

    persona = _persona_by_id(cfg, page.get("persona", ""))
    try:
        recent_formats = get_recent_formats()
    except Exception:
        recent_formats = []
    box = (page.get("matrix_job", ""), page.get("matrix_stage", ""))
    candidates = formats_for_box(box, cfg) if all(box) else free_formats(cfg)
    post_format = pick_format(winner, recent_formats, candidates=candidates)

    chosen_asset = None
    try:
        chosen_asset = asset_for_format(post_format, cfg, get_recent_assets())
    except Exception as e:
        print(f"  Asset-Wahl fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if post_format in FORMAT_ASSET_ATTR and not chosen_asset:
        post_format = pick_format(winner, recent_formats, candidates=free_formats(cfg))
    if persona and post_format in FORMAT_ASSET_ATTR:
        personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
        dominant = next((p for p in personas if p.get("share") == "dominant"), None)
        if dominant:
            persona = dominant

    try:
        recent_infographic_types = get_recent_infographic_types()
    except Exception:
        recent_infographic_types = []
    try:
        recent_archetypes = get_recent_archetypes()
    except Exception:
        recent_archetypes = []

    linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext = \
        generate_post_and_image_prompt(
            winner, post_format,
            recent_infographic_types=recent_infographic_types,
            assets_de=assets_block(post_format, chosen_asset, "de"),
            assets_en=assets_block(post_format, chosen_asset, "en"),
            persona_de=persona_block(persona, "de"),
            persona_en=persona_block(persona, "en"),
            persona_voice_de=(persona or {}).get("voice_de", ""),
        )
    if not linkedin_draft:
        print(f"  Leerer Draft fuer {page['post_url']} - Skip.", file=sys.stderr)
        return

    if post_format == "CaseProof" and chosen_asset:
        for attempt in ("retry", "downgrade"):
            if figures_ok(f"{linkedin_draft}\n{en_draft}", chosen_asset):
                break
            if attempt == "retry":
                print("  Zahlen-Guard verletzt - ein Retry.", file=sys.stderr)
                linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext = \
                    generate_post_and_image_prompt(
                        winner, post_format,
                        recent_infographic_types=recent_infographic_types,
                        assets_de=assets_block(post_format, chosen_asset, "de"),
                        assets_en=assets_block(post_format, chosen_asset, "en"),
                        persona_de=persona_block(persona, "de"),
                        persona_en=persona_block(persona, "en"),
                    )
            else:
                print("  Zahlen-Guard erneut verletzt - Downgrade auf Method.", file=sys.stderr)
                post_format = "Method"
                chosen_asset = None
                linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext = \
                    generate_post_and_image_prompt(
                        winner, post_format,
                        recent_infographic_types=recent_infographic_types,
                        persona_de=persona_block(persona, "de"),
                        persona_en=persona_block(persona, "en"),
                    )
        if not linkedin_draft:
            print(f"  Leerer Draft nach Guard fuer {page['post_url']} - Skip.",
                  file=sys.stderr)
            return

    infographic_type = normalize_infographic_type(parse_infographic_type(skeleton))
    sig = skeleton_signals(skeleton, sound_byte)
    chosen_archetype = select_archetype(
        post_format=post_format, infographic_type=infographic_type,
        layers_count=sig["layers_count"], has_metaphor=sig["has_metaphor"],
        has_stat=sig["has_stat"], recent_archetypes=recent_archetypes)
    gen_archetype, gen_prompt, gen_ratio, gen_strip = build_archetype_prompt(
        chosen_archetype, soundbyte=sound_byte, kontext=kontext, skeleton=skeleton,
        language=getattr(cfg, "IMAGE_LANGUAGE", "English"))

    matrix_box = FORMAT_TO_BOX.get(post_format, ("", ""))
    update_with_draft(
        page_id=page["page_id"],
        linkedin_draft=linkedin_draft,
        en_draft="",
        image_prompt=gen_prompt,
        image_url="",
        title=winner.get("post_excerpt", "")[:60],
        influencer=winner["influencer"],
        image_failed=False,
        image_error="",
        infographic_skeleton=skeleton,
        post_format=post_format,
        infographic_type=infographic_type,
        archetype=gen_archetype,
        matrix_job=matrix_box[0],
        matrix_stage=matrix_box[1],
        persona=(persona or {}).get("id", ""),
        poster=page.get("poster", ""),
        asset_id=(chosen_asset or {}).get("id", ""),
        post_text=winner["post_text"],
        post_url=winner["post_url"],
    )
    set_state([page["post_url"]], "picked")
    print(f"  Draft geschrieben: {page['post_url']} ({post_format})")
