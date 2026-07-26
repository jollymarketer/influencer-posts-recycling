"""CTA-Politik, Magnet-Slots, Engagement-Matching und Kommentar-Verteilung
(Distributions-Umbau Richard 2026-07-26)."""
import importlib
import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_slate
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
