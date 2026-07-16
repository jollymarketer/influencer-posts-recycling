"""Phase C: Guard, Archiv+Strike, Pool-Abort, Slate-Schreiben."""
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
)
MON = datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc)  # Montag


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
        "score_posts": MagicMock(return_value=[]),
        "get_recent_boxes": MagicMock(return_value=[]),
        "pick_target_box": MagicMock(return_value=None),
        "create_slate_entry": MagicMock(return_value="page-1"),
        "set_state": MagicMock(),
    }
    mocks.update(overrides)
    return patch.multiple(run_slate, **mocks), mocks


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


def test_pool_error_aborts_without_slate():
    ctx, mocks = _patch_all(
        get_candidates=MagicMock(side_effect=RuntimeError("supabase down")))
    with ctx:
        run_slate.phase_slate(CFG, MON)  # darf nicht raisen
    mocks["create_slate_entry"].assert_not_called()
    mocks["set_meta"].assert_not_called()


def test_slate_written_and_pool_updated():
    pool_row = {"post_url": "u1", "influencer": "A", "post_text": "t",
                "post_date": "2026-07-15", "likes": 1, "comments": 0, "shares": 0}
    scored = [{"post_url": "u1", "influencer": "A", "post_text": "t",
               "score": 40, "score_details": {}, "reasoning": "r",
               "persona": "kaeufer", "voc_hit": "", "topic_angle_de": "Winkel",
               "matrix_job": "Proof", "matrix_stage": "Education"}]
    ctx, mocks = _patch_all(
        get_candidates=MagicMock(return_value=[pool_row]),
        score_posts=MagicMock(return_value=scored),
        pick_target_box=MagicMock(return_value=("Proof", "Education")))
    with ctx:
        run_slate.phase_slate(CFG, MON)
    call = mocks["create_slate_entry"].call_args
    prio = call.kwargs.get("matrix_prio", call.args[1] if len(call.args) > 1 else None)
    assert prio is True
    mocks["set_state"].assert_called_once()
    assert mocks["set_state"].call_args.args[0] == ["u1"]
    assert mocks["set_state"].call_args.args[1] == "slated"
    mocks["set_meta"].assert_called_once_with("last_slate_at_lisocon", "2026-07-20")
