"""CTA-Politik, Magnet-Slots, Engagement-Matching und Kommentar-Verteilung
(Distributions-Umbau Richard 2026-07-26)."""
import importlib
import os
import sys
import types
from contextlib import ExitStack
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_slate
from tools import comment_drafts as cd
from tools.engagement_readback import extract_ids, match_row
from tools.comment_drafts import assign_posts, rotate_profiles

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")


def _cfg(**kw):
    base = dict(LEAD_MAGNETS=[{"id": "m"}], MAGNET_SLOTS_PER_SLATE=2,
                CONTENT_PERSONAS=[{"id": "kaeufer", "share": "dominant"},
                                  {"id": "anwender", "share": "secondary"}])
    base.update(kw)
    return types.SimpleNamespace(**base)


def _slate(kaeufer=5, anwender=5):
    return ([{"persona": "kaeufer", "post_url": f"k{i}"} for i in range(kaeufer)]
            + [{"persona": "anwender", "post_url": f"a{i}"} for i in range(anwender)])


# --- CTA-Politik -------------------------------------------------------------

def test_lisocon_runs_magnet_only_cta_policy():
    assert lisocon.CTA_POLICY == "magnet_only"
    # Jolly bleibt unveraendert auf dem Blanket-CTA.
    assert getattr(jolly, "CTA_POLICY", "always") == "always"


def test_blanket_cta_suppressed_for_lisocon_and_asset_formats(monkeypatch):
    from tools import post_scorer

    monkeypatch.setattr(post_scorer, "_cfg",
                        types.SimpleNamespace(CTA_POLICY="magnet_only",
                                              CTA_DE="LINK", CTA_EN="LINK"))
    assert post_scorer.blanket_cta("Opinion", "CTA_DE") == ""
    assert post_scorer.blanket_cta("Magnet", "CTA_DE") == ""

    monkeypatch.setattr(post_scorer, "_cfg",
                        types.SimpleNamespace(CTA_POLICY="always",
                                              CTA_DE="LINK", CTA_EN="LINK"))
    assert post_scorer.blanket_cta("Opinion", "CTA_DE") == "LINK"
    # Magnet/Offer bringen ihren CTA aus dem Asset-Block mit - nie zwei CTAs.
    assert post_scorer.blanket_cta("Magnet", "CTA_DE") == ""
    assert post_scorer.blanket_cta("Offer", "CTA_EN") == ""


# --- Magnet-Slots ------------------------------------------------------------

def test_magnet_slots_one_per_persona_side():
    slots = run_slate.pick_magnet_slots(_slate(), _cfg())
    assert len(slots) == 2
    personas = {_slate()[i]["persona"] for i in slots}
    assert personas == {"kaeufer", "anwender"}


def test_magnet_slots_skip_strongest_and_weakest_candidate():
    slots = sorted(run_slate.pick_magnet_slots(_slate(), _cfg()))
    assert slots == [2, 7]          # jeweils der mittlere der 5er-Gruppe


def test_magnet_slots_off_without_magnets_or_quota():
    assert run_slate.pick_magnet_slots(_slate(), _cfg(LEAD_MAGNETS=[])) == set()
    assert run_slate.pick_magnet_slots(_slate(), _cfg(MAGNET_SLOTS_PER_SLATE=0)) == set()


def test_magnet_slots_prefer_dominant_persona_when_only_one_slot():
    slots = run_slate.pick_magnet_slots(_slate(), _cfg(MAGNET_SLOTS_PER_SLATE=1))
    assert slots == {2}             # kaeufer-Seite zuerst, nicht alphabetisch


def test_lisocon_config_declares_two_magnet_slots():
    assert lisocon.MAGNET_SLOTS_PER_SLATE == 2
    assert lisocon.MAGNET_SLOTS_PER_SLATE == lisocon.MATRIX["promotion_cap"]


# --- Engagement-Readback -----------------------------------------------------

def test_extract_ids_reads_share_urn_and_feed_url():
    assert extract_ids("https://www.linkedin.com/feed/update/urn:li:share:7486012312672448513/") \
        == {"7486012312672448513"}
    assert extract_ids("urn:li:activity:7486012312672448513") == {"7486012312672448513"}
    assert extract_ids("", None, 17) == set()


def test_match_row_pairs_notion_row_with_scraped_post():
    row = {"live_url": "https://www.linkedin.com/feed/update/urn:li:share:7486012312672448513/"}
    items = [{"linkedinUrl": "https://www.linkedin.com/posts/other-1111111111111111111"},
             {"linkedinUrl": "https://www.linkedin.com/posts/x", "shareUrn": "urn:li:share:7486012312672448513"}]
    assert match_row(row, items) is items[1]


def test_match_row_without_url_never_guesses():
    assert match_row({"live_url": ""}, [{"linkedinUrl": "urn:li:share:7486012312672448513"}]) is None


# --- Kommentar-Entwuerfe -----------------------------------------------------

def test_rotate_profiles_covers_full_pool_over_days():
    pool = [{"name": f"p{i}", "linkedin_url": f"u{i}"} for i in range(39)]
    seen = set()
    for day in range(4):
        seen |= {p["name"] for p in rotate_profiles(pool, 12, day)}
    assert len(seen) == 39


def test_rotate_profiles_handles_short_pool():
    pool = [{"name": "a", "linkedin_url": "u"}]
    assert len(rotate_profiles(pool, 12, 5)) == 1
    assert rotate_profiles([], 12, 0) == []


def test_assign_posts_never_gives_one_post_to_two_posters():
    posts = [{"post_url": f"p{i}"} for i in range(6)]
    pairs = assign_posts(posts, ["Reinhard", "Jae"], 3)
    assert len(pairs) == 6
    assert len({p["post_url"] for _, p in pairs}) == 6
    # Abwechselnd, damit beide die frischesten Posts sehen.
    assert [poster for poster, _ in pairs][:4] == ["Reinhard", "Jae", "Reinhard", "Jae"]


def test_assign_posts_stops_when_queue_runs_dry():
    pairs = assign_posts([{"post_url": "p0"}], ["Reinhard", "Jae"], 3)
    assert len(pairs) == 1


# --- Tages-Guard Kommentar-Entwuerfe ----------------------------------------

MON = datetime(2026, 7, 27, 5, 0, tzinfo=timezone.utc)
_GUARD_CFG = types.SimpleNamespace(
    NAME="lisocon", COMMENT_DRAFTS={"profiles_per_day": 2, "drafts_per_poster": 1,
                                    "posters": ["Reinhard"]},
    CONTENT_PERSONAS=[], TOKENS={}, CONTEXT="x", POSTER_DEFAULT="Reinhard")


def _patch_comments(**kw):
    defaults = dict(
        get_meta=MagicMock(return_value=""),
        set_meta=MagicMock(),
        get_comment_target_urls=MagicMock(return_value=set()),
        load_influencers=MagicMock(return_value=[{"name": "n", "linkedin_url": "u"}]),
        fetch_fresh_posts=MagicMock(return_value=[{"post_url": "p0", "post_text": "t",
                                                   "influencer": "n", "age_hours": 2}]),
        draft_comment=MagicMock(return_value={"title": "t", "comment": "c",
                                              "poster": "Reinhard", "target_url": "p0",
                                              "influencer": "n", "excerpt": "e"}),
        create_comment_entry=MagicMock(return_value="page"),
        _notify=MagicMock(),
    )
    defaults.update(kw)
    ctx = ExitStack()
    mocks = {}
    for name, mock in defaults.items():
        ctx.enter_context(patch.object(cd, name, mock))
        mocks[name] = mock
    return ctx, mocks


def test_second_daily_slot_skips_when_guard_is_set():
    ctx, mocks = _patch_comments(get_meta=MagicMock(return_value="2026-07-27"))
    with ctx:
        assert cd.run_comment_drafts(_GUARD_CFG, MON) == 0
    mocks["fetch_fresh_posts"].assert_not_called()
    mocks["create_comment_entry"].assert_not_called()


def test_guard_set_only_after_a_draft_was_written():
    ctx, mocks = _patch_comments()
    with ctx:
        assert cd.run_comment_drafts(_GUARD_CFG, MON) == 1
    mocks["set_meta"].assert_called_once_with("last_comments_at_lisocon", "2026-07-27")


def test_empty_morning_run_leaves_guard_open_for_the_second_slot():
    ctx, mocks = _patch_comments(fetch_fresh_posts=MagicMock(return_value=[]))
    with ctx:
        assert cd.run_comment_drafts(_GUARD_CFG, MON) == 0
    mocks["set_meta"].assert_not_called()


def test_unreadable_guard_never_blocks_the_run():
    ctx, mocks = _patch_comments(get_meta=MagicMock(side_effect=RuntimeError("supabase down")))
    with ctx:
        assert cd.run_comment_drafts(_GUARD_CFG, MON) == 1
    mocks["create_comment_entry"].assert_called_once()
