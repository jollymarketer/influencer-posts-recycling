"""Slate-Modus-Phasen (Amendment 2026-07-17: Draft im Slate-Bau, Pick=Approved).
Phase C: Guard, Archiv+Strike, picked-Detection, Pool-Abort, Slate-mit-Draft.
Phase A: Bild-Wrapper. Dispatch: Wochentags-Gating, kein Phase-B mehr."""
import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_slate

CFG = SimpleNamespace(
    NAME="lisocon",
    SLATE={"days": (0, 3), "size": 10, "per_persona": 5,
           "max_age_days": 60, "max_times_slated": 3},
    FEATURES={"slate_mode": True, "keyword_source_daily": False},
    CONTENT_PERSONAS=[{"id": "kaeufer", "share": "dominant"}, {"id": "anwender"}],
    POSTER_BY_PERSONA={"kaeufer": "Reinhard", "anwender": "Jae"},
    POSTER_DEFAULT="Reinhard",
    IMAGE_LANGUAGE="German",
)
MON = datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc)  # Montag

_DRAFT = {"linkedin_draft": "DE Draft", "image_prompt": "prompt",
          "skeleton": "skelett", "post_format": "POV",
          "infographic_type": "Iceberg", "archetype": "stat_hero"}


def _patch_all(**overrides):
    mocks = {
        "get_meta": MagicMock(return_value=""),
        "set_meta": MagicMock(),
        "get_pages_by_status": MagicMock(return_value=[]),
        "archive_page": MagicMock(),
        "unslate_and_strike": MagicMock(),
        "retire_aged": MagicMock(return_value=0),
        "get_existing_post_urls": MagicMock(return_value=set()),
        "get_pool_urls": MagicMock(return_value=set()),
        "scrape_all_sources": MagicMock(return_value=[]),
        "upsert_candidates": MagicMock(return_value=0),
        "get_candidates": MagicMock(return_value=[]),
        "get_recent_linkedin_drafts": MagicMock(return_value=[]),
        "get_recent_formats": MagicMock(return_value=[]),
        "get_recent_infographic_types": MagicMock(return_value=[]),
        "get_recent_archetypes": MagicMock(return_value=[]),
        "score_posts": MagicMock(return_value=[]),
        "get_recent_boxes": MagicMock(return_value=[]),
        "pick_target_box": MagicMock(return_value=None),
        "draft_candidate": MagicMock(return_value=dict(_DRAFT)),
        "create_slate_entry": MagicMock(return_value="page-1"),
        "set_state": MagicMock(),
    }
    mocks.update(overrides)
    return patch.multiple(run_slate, **mocks), mocks


def _pool_row(url="u1", persona="kaeufer"):
    return {"post_url": url, "influencer": "A", "post_text": "t",
            "post_date": "2026-07-15", "likes": 1, "comments": 0, "shares": 0,
            "persona": persona}


def _scored(url="u1", persona="kaeufer", score=40):
    return {"post_url": url, "influencer": "A", "post_text": "t",
            "score": score, "score_details": {}, "reasoning": "r",
            "persona": persona, "voc_hit": "", "topic_angle_de": "Winkel",
            "matrix_job": "Proof", "matrix_stage": "Education"}


def test_guard_skips_second_run_same_day():
    ctx, mocks = _patch_all(get_meta=MagicMock(return_value="2026-07-20"))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    mocks["scrape_all_sources"].assert_not_called()
    mocks["set_meta"].assert_not_called()


def test_previous_slate_archived_and_striked():
    prev = [{"page_id": "p1", "post_url": "u1", "persona": "kaeufer",
             "poster": "Reinhard", "matrix_job": "", "matrix_stage": ""}]
    ctx, mocks = _patch_all(get_pages_by_status=MagicMock(return_value=prev))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    mocks["archive_page"].assert_called_once_with("p1")
    mocks["unslate_and_strike"].assert_called_once_with(["u1"], 3)


def test_picked_candidates_detected_before_strike():
    """Gepickte Slate-Zeilen sind nicht mehr Themenvorschlag -> Pool-State picked."""
    prev = [{"page_id": "p1", "post_url": "u1", "persona": "kaeufer",
             "poster": "Reinhard", "matrix_job": "", "matrix_stage": ""}]

    def get_candidates_side_effect(client, states):
        if states == ["slated"]:
            return [_pool_row("u1"), _pool_row("u2")]  # u2 wurde gepickt
        return []

    ctx, mocks = _patch_all(
        get_pages_by_status=MagicMock(return_value=prev),
        get_candidates=MagicMock(side_effect=get_candidates_side_effect))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    picked_calls = [c for c in mocks["set_state"].call_args_list
                    if c.args[1] == "picked"]
    assert len(picked_calls) == 1
    assert picked_calls[0].args[0] == ["u2"]


def test_pool_error_aborts_without_slate():
    ctx, mocks = _patch_all(
        get_candidates=MagicMock(side_effect=RuntimeError("supabase down")))
    with ctx:
        run_slate.phase_slate(CFG, MON)  # darf nicht raisen
    mocks["create_slate_entry"].assert_not_called()
    mocks["set_meta"].assert_not_called()


def test_slate_written_with_draft_and_pool_updated():
    def get_candidates_side_effect(client, states):
        if states == ["pool"]:
            return [_pool_row("u1")]
        return []

    ctx, mocks = _patch_all(
        get_candidates=MagicMock(side_effect=get_candidates_side_effect),
        score_posts=MagicMock(return_value=[_scored("u1")]),
        pick_target_box=MagicMock(return_value=("Proof", "Education")))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    call = mocks["create_slate_entry"].call_args
    assert call.kwargs["draft"]["linkedin_draft"] == "DE Draft"
    prio = call.kwargs.get("matrix_prio", call.args[1] if len(call.args) > 1 else None)
    assert prio is True
    slated_calls = [c for c in mocks["set_state"].call_args_list
                    if c.args[1] == "slated"]
    assert slated_calls[0].args[0] == ["u1"]
    mocks["set_meta"].assert_called_once_with("last_slate_at_lisocon", "2026-07-20")


def test_draft_failure_skips_row_keeps_candidate_in_pool():
    def get_candidates_side_effect(client, states):
        if states == ["pool"]:
            return [_pool_row("u1"), _pool_row("u2", persona="anwender")]
        return []

    def draft_side_effect(cfg, winner, persona_id, box, recents):
        if winner["post_url"] == "u1":
            raise RuntimeError("sonnet down")
        return dict(_DRAFT)

    ctx, mocks = _patch_all(
        get_candidates=MagicMock(side_effect=get_candidates_side_effect),
        score_posts=MagicMock(return_value=[_scored("u1"), _scored("u2", "anwender")]),
        draft_candidate=MagicMock(side_effect=draft_side_effect))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    assert mocks["create_slate_entry"].call_count == 1  # nur u2
    slated_calls = [c for c in mocks["set_state"].call_args_list
                    if c.args[1] == "slated"]
    assert slated_calls[0].args[0] == ["u2"]


def test_in_run_anti_repeat_grows_recents():
    """Jeder Draft im Lauf sieht die im selben Lauf schon vergebenen Werte."""
    def get_candidates_side_effect(client, states):
        if states == ["pool"]:
            return [_pool_row("u1"), _pool_row("u2", persona="anwender")]
        return []

    seen = []

    def draft_side_effect(cfg, winner, persona_id, box, recents):
        seen.append([list(recents["formats"]), list(recents["infographic_types"]),
                     list(recents["archetypes"])])
        return dict(_DRAFT)

    ctx, mocks = _patch_all(
        get_candidates=MagicMock(side_effect=get_candidates_side_effect),
        score_posts=MagicMock(return_value=[_scored("u1"), _scored("u2", "anwender")]),
        draft_candidate=MagicMock(side_effect=draft_side_effect))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    assert seen[0] == [[], [], []]
    assert seen[1][0][0] == "POV"           # Format des ersten Drafts
    assert seen[1][1][0] == "Iceberg"       # Infografik-Typ
    assert seen[1][2][0] == "stat_hero"     # Archetyp


def test_single_format_box_breaks_clump_after_two_in_a_row():
    """Ein-Format-Boxen (z.B. Perspective x Awareness -> nur Opinion) umgehen
    das pick_format-Anti-Repeat. Clamp: steht das erzwungene Format schon 2x
    in Folge im Lauf-Kontext, faellt die Wahl auf free_formats zurueck
    (Befund Slate-Lauf 17.07: 9x Opinion)."""
    winner = _scored("u1")
    recents = {"formats": ["Opinion", "Opinion", "POV"],
               "infographic_types": [], "archetypes": []}
    captured = {}

    def fake_pick_format(w, recent, candidates=None):
        captured["candidates"] = list(candidates)
        return "Story"

    with patch.object(run_slate, "formats_for_box", return_value=["Opinion"]), \
         patch.object(run_slate, "free_formats", return_value=["Opinion", "POV", "Story"]) as ff, \
         patch.object(run_slate, "pick_format", side_effect=fake_pick_format), \
         patch.object(run_slate, "asset_for_format", return_value=None), \
         patch.object(run_slate, "get_recent_assets", return_value=[]), \
         patch.object(run_slate, "generate_post_and_image_prompt",
                      return_value=("Draft", "", "prompt", "skelett", "sb", "ktx")), \
         patch.object(run_slate, "normalize_infographic_type", return_value="Iceberg"), \
         patch.object(run_slate, "parse_infographic_type", return_value="Iceberg"), \
         patch.object(run_slate, "skeleton_signals",
                      return_value={"layers_count": 0, "has_metaphor": False, "has_stat": False}), \
         patch.object(run_slate, "select_archetype", return_value="stat_hero"), \
         patch.object(run_slate, "build_archetype_prompt",
                      return_value=("stat_hero", "prompt", "1:1", True)):
        result = run_slate.draft_candidate(CFG, winner, "kaeufer",
                                           ("Perspective", "Awareness"), recents)
    ff.assert_called()
    assert captured["candidates"] == ["Opinion", "POV", "Story"]
    assert result["post_format"] == "Story"


def test_single_format_box_respected_when_not_clumped():
    """Erste/zweite Nutzung der Ein-Format-Box: Quota schlaegt Anti-Repeat."""
    winner = _scored("u1")
    recents = {"formats": ["Opinion", "POV"], "infographic_types": [], "archetypes": []}
    with patch.object(run_slate, "formats_for_box", return_value=["Opinion"]), \
         patch.object(run_slate, "pick_format", side_effect=lambda w, r, candidates: candidates[0]), \
         patch.object(run_slate, "asset_for_format", return_value=None), \
         patch.object(run_slate, "get_recent_assets", return_value=[]), \
         patch.object(run_slate, "generate_post_and_image_prompt",
                      return_value=("Draft", "", "prompt", "skelett", "sb", "ktx")), \
         patch.object(run_slate, "normalize_infographic_type", return_value="Iceberg"), \
         patch.object(run_slate, "parse_infographic_type", return_value="Iceberg"), \
         patch.object(run_slate, "skeleton_signals",
                      return_value={"layers_count": 0, "has_metaphor": False, "has_stat": False}), \
         patch.object(run_slate, "select_archetype", return_value="stat_hero"), \
         patch.object(run_slate, "build_archetype_prompt",
                      return_value=("stat_hero", "prompt", "1:1", True)):
        result = run_slate.draft_candidate(CFG, winner, "kaeufer",
                                           ("Perspective", "Awareness"), recents)
    assert result["post_format"] == "Opinion"


def test_phase_images_nonfatal():
    with patch.object(run_slate, "fill_missing_images",
                      MagicMock(side_effect=RuntimeError("kie down"))):
        run_slate.phase_images(CFG)  # darf nicht raisen


def test_phase_images_reports_count(capsys):
    with patch.object(run_slate, "fill_missing_images", MagicMock(return_value=2)):
        run_slate.phase_images(CFG)
    assert "2" in capsys.readouterr().out


def test_run_slate_mode_weekday_gating():
    thu = datetime(2026, 7, 23, 7, 0, tzinfo=timezone.utc)   # Donnerstag
    tue = datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc)   # Dienstag
    with patch.object(run_slate, "phase_images") as pi, \
         patch.object(run_slate, "phase_slate") as ps:
        run_slate.run_slate_mode(CFG, now=thu)
        run_slate.run_slate_mode(CFG, now=tue)
    assert pi.call_count == 2
    ps.assert_called_once()          # nur Donnerstag
    assert ps.call_args.args[1] == thu


def test_no_phase_drafts_anymore():
    """Phase B ist raus (Pick = Approved, kein Zwischenschritt)."""
    assert not hasattr(run_slate, "phase_drafts")


def test_run_research_dispatches_to_slate_mode(monkeypatch):
    import run_research
    monkeypatch.setattr(run_research._cfg, "FEATURES",
                        {**run_research._cfg.FEATURES, "slate_mode": True},
                        raising=False)
    called = {}
    monkeypatch.setattr(run_slate, "run_slate_mode",
                        lambda cfg, now=None: called.setdefault("yes", True))
    run_research.main(now=datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc))
    assert called.get("yes") is True
