"""
Lisocon Slate-Modus (spec docs/superpowers/specs/2026-07-16-lisocon-topic-slate-pool-design.md,
Amendment 2026-07-17: Drafts entstehen schon im Slate-Bau, Pick = Approved).

Zwei Phasen pro Cron-Lauf (Mo-Fr 07:00 UTC):
  A (immer):  Status=Approved ohne Bild -> Bild generieren (teuerster Schritt,
              laeuft erst nach dem menschlichen Pick)
  C (Mo+Do):  Scrape -> Pool -> Re-Score -> 10er-Slate MIT fertigen Drafts
              nach Notion. Jae liest den Post beim Picken; der Approved-Flip
              ist die einzige menschliche Geste.

Nur aktiv bei FEATURES["slate_mode"] (lisocon). Jolly: run_research.run_daily.
"""
import os
import sys
from datetime import datetime, timezone

import requests

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
)
from tools.topic_pool import (
    upsert_candidates,
    get_pool_urls,
    get_candidates,
    set_state,
    unslate_and_strike,
    retire_aged,
    revive_picked,
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
        prev_urls = {r["post_url"] for r in prev if r["post_url"]}
        # Gepickte Slate-Zeilen sind nicht mehr Themenvorschlag (Approved/
        # Posted) -> Pool-State picked, bevor die Verbliebenen gestriked werden.
        picked = [r["post_url"] for r in get_candidates(cfg.NAME, ["slated"])
                  if r["post_url"] not in prev_urls]
        if picked:
            set_state(picked, "picked")
        for row in prev:
            archive_page(row["page_id"])
        unslate_and_strike(sorted(prev_urls), slate_cfg["max_times_slated"])
        retired = retire_aged(cfg.NAME, slate_cfg["max_age_days"])
        if retired:
            print(f"  {retired} Kandidat(en) altersbedingt retired.")
        revive_days = slate_cfg.get("revive_picked_days")
        if revive_days:
            revived = revive_picked(cfg.NAME, revive_days)
            if revived:
                print(f"  {revived} gepickte(r) Kandidat(en) fuer Winner-Repeat zurueck im Pool.")
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

    # Anti-Repeat-Kontext: Seed aus Notion (Posted/Approved), waechst im Lauf
    # mit jedem generierten Draft (20 Drafts sehen sonst denselben Stand und
    # klumpen auf ein Format / einen Infografik-Typ / einen Bild-Stil).
    recents = {"formats": [], "infographic_types": [], "archetypes": []}
    for key, getter in (("formats", get_recent_formats),
                        ("infographic_types", get_recent_infographic_types),
                        ("archetypes", get_recent_archetypes)):
        try:
            recents[key] = getter()
        except Exception:
            pass

    written = []
    for cand in slate:
        prio = bool(target_box) and (cand.get("matrix_job", ""),
                                     cand.get("matrix_stage", "")) == target_box
        box = (cand.get("matrix_job", ""), cand.get("matrix_stage", ""))
        try:
            draft = draft_candidate(cfg, cand, cand.get("persona", ""), box, recents)
            if not draft:
                print(f"  Kein Draft fuer {cand['post_url']} - Skip.", file=sys.stderr)
                continue
            create_slate_entry(cand, matrix_prio=prio, draft=draft)
            written.append(cand["post_url"])
            for key, field in (("formats", "post_format"),
                               ("infographic_types", "infographic_type"),
                               ("archetypes", "archetype")):
                if draft.get(field):
                    recents[key].insert(0, draft[field])
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
    if written:
        _notify_slate(cfg, len(written), today)


def _notify_slate(cfg, count: int, date: str) -> None:
    """Slate-Ready-Mail an Jae via Make (Szenario 9537326). Non-fatal;
    ohne MAKE_SLATE_WEBHOOK-Env stiller Skip."""
    url = os.environ.get("MAKE_SLATE_WEBHOOK", "")
    if not url:
        print("  Slate-Benachrichtigung uebersprungen: MAKE_SLATE_WEBHOOK nicht gesetzt.")
        return
    try:
        requests.post(url, json={
            "count": count,
            "date": date,
            "view_url": getattr(cfg, "SLATE_VIEW_URL", ""),
        }, timeout=15)
        print("  Slate-Benachrichtigung an Make gefeuert.")
    except Exception as e:
        print(f"  Slate-Benachrichtigung fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)


def run_slate_mode(cfg, now=None) -> None:
    now = now or datetime.now(timezone.utc)
    print(f"=== Slate-Modus (Client: {cfg.NAME}) — {now.strftime('%Y-%m-%d %H:%M UTC')} ===")
    phase_images(cfg)
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


def draft_candidate(cfg, winner: dict, persona_id: str, box: tuple, recents: dict) -> dict | None:
    """Erzeugt Draft + Bild-Prompt fuer einen Slate-Kandidaten (Amendment
    2026-07-17). Kein Notion-Zugriff: Anti-Repeat-Kontext kommt als `recents`
    ({"formats", "infographic_types", "archetypes"}) vom Aufrufer und waechst
    dort pro Lauf. Rueckgabe-Dict fuer create_slate_entry(draft=...), None bei
    leerem Draft."""
    persona = _persona_by_id(cfg, persona_id)
    candidates = formats_for_box(box, cfg) if all(box) else free_formats(cfg)
    # Klumpen-Clamp (Befund 17.07: 9x Opinion): Ein-Format-Boxen umgehen das
    # pick_format-Anti-Repeat ("Quota schlaegt Wiederholung"). Steht das
    # erzwungene Format schon 2x in Folge im Lauf-Kontext, freie Wahl.
    if len(candidates) == 1 and recents["formats"][:2] == [candidates[0]] * 2:
        candidates = free_formats(cfg)
    post_format = pick_format(winner, recents["formats"], candidates=candidates)

    chosen_asset = None
    try:
        chosen_asset = asset_for_format(post_format, cfg, get_recent_assets())
    except Exception as e:
        print(f"  Asset-Wahl fehlgeschlagen (nicht kritisch): {e}", file=sys.stderr)
    if post_format in FORMAT_ASSET_ATTR and not chosen_asset:
        post_format = pick_format(winner, recents["formats"], candidates=free_formats(cfg))
    if persona and post_format in FORMAT_ASSET_ATTR:
        personas = getattr(cfg, "CONTENT_PERSONAS", None) or []
        dominant = next((p for p in personas if p.get("share") == "dominant"), None)
        if dominant:
            persona = dominant

    linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext =         generate_post_and_image_prompt(
            winner, post_format,
            recent_infographic_types=recents["infographic_types"],
            assets_de=assets_block(post_format, chosen_asset, "de"),
            assets_en=assets_block(post_format, chosen_asset, "en"),
            persona_de=persona_block(persona, "de"),
            persona_en=persona_block(persona, "en"),
            persona_voice_de=(persona or {}).get("voice_de", ""),
        )
    if not linkedin_draft:
        return None

    if post_format == "CaseProof" and chosen_asset:
        for attempt in ("retry", "downgrade"):
            if figures_ok(f"{linkedin_draft}\n{en_draft}", chosen_asset):
                break
            if attempt == "retry":
                print("  Zahlen-Guard verletzt - ein Retry.", file=sys.stderr)
                linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext =                     generate_post_and_image_prompt(
                        winner, post_format,
                        recent_infographic_types=recents["infographic_types"],
                        assets_de=assets_block(post_format, chosen_asset, "de"),
                        assets_en=assets_block(post_format, chosen_asset, "en"),
                        persona_de=persona_block(persona, "de"),
                        persona_en=persona_block(persona, "en"),
                    )
            else:
                print("  Zahlen-Guard erneut verletzt - Downgrade auf Method.", file=sys.stderr)
                post_format = "Method"
                chosen_asset = None
                linkedin_draft, en_draft, image_prompt, skeleton, sound_byte, kontext =                     generate_post_and_image_prompt(
                        winner, post_format,
                        recent_infographic_types=recents["infographic_types"],
                        persona_de=persona_block(persona, "de"),
                        persona_en=persona_block(persona, "en"),
                    )
        if not linkedin_draft:
            return None

    infographic_type = normalize_infographic_type(parse_infographic_type(skeleton))
    sig = skeleton_signals(skeleton, sound_byte)
    chosen_archetype = select_archetype(
        post_format=post_format, infographic_type=infographic_type,
        layers_count=sig["layers_count"], has_metaphor=sig["has_metaphor"],
        has_stat=sig["has_stat"], recent_archetypes=recents["archetypes"])
    gen_archetype, gen_prompt, gen_ratio, gen_strip = build_archetype_prompt(
        chosen_archetype, soundbyte=sound_byte, kontext=kontext, skeleton=skeleton,
        language=getattr(cfg, "IMAGE_LANGUAGE", "English"))

    return {
        "linkedin_draft": linkedin_draft,
        "image_prompt": gen_prompt,
        "skeleton": skeleton,
        "post_format": post_format,
        "infographic_type": infographic_type,
        "archetype": gen_archetype,
    }
