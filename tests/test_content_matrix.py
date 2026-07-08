"""Tests for the content matrix box model and quota logic. Pure functions."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import content_matrix as cm

ALL_BOXES = [(j, s) for j in cm.JOBS for s in cm.STAGES]


def _cfg(boxes=None, proof=None, offers=None, magnets=None,
         mix=None, floor=2, cap=2):
    matrix = None
    if boxes is not None:
        matrix = {
            "mix": mix or {"Perspective": 5, "Proof": 3, "Promotion": 2},
            "selection_floor": floor,
            "promotion_cap": cap,
            "boxes": boxes,
        }
    return SimpleNamespace(
        MATRIX=matrix,
        PROOF_ASSETS=proof or [],
        OFFERS=offers or [],
        LEAD_MAGNETS=magnets or [],
    )


def test_box_model_is_complete():
    assert set(cm.BOX_FORMATS) == set(ALL_BOXES)
    # every format maps back to exactly one box
    for box, formats in cm.BOX_FORMATS.items():
        for f in formats:
            assert cm.FORMAT_TO_BOX[f] == box
    assert set(cm.PROMOTION_FORMATS) == {"Debate", "Magnet", "Offer"}


def test_effective_boxes_drops_asset_gated_boxes_without_assets():
    cfg = _cfg(boxes=ALL_BOXES)  # all 9 declared, no assets
    eff = cm.effective_boxes(cfg)
    assert ("Proof", "Selection") not in eff
    assert ("Promotion", "Education") not in eff
    assert ("Promotion", "Selection") not in eff
    assert len(eff) == 6


def test_effective_boxes_with_assets_keeps_all_nine():
    cfg = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}],
               offers=[{"id": "b"}], magnets=[{"id": "c"}])
    assert len(cm.effective_boxes(cfg)) == 9


def test_effective_boxes_respects_declared_whitelist():
    boxes = [b for b in ALL_BOXES if b != ("Promotion", "Selection")]
    cfg = _cfg(boxes=boxes, proof=[{"id": "a"}], offers=[{"id": "b"}])
    eff = cm.effective_boxes(cfg)
    assert ("Promotion", "Selection") not in eff  # declared out stays out
    assert ("Proof", "Selection") in eff


def test_effective_boxes_empty_when_matrix_missing():
    cfg = SimpleNamespace()  # tenant without MATRIX
    assert cm.effective_boxes(cfg) == []


def test_formats_for_box_and_free_formats():
    cfg = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}],
               offers=[{"id": "b"}], magnets=[{"id": "c"}])
    assert cm.formats_for_box(("Perspective", "Education"), cfg) == ["POV", "Signature"]
    assert cm.formats_for_box(("Proof", "Selection"), cfg) == ["CaseProof"]
    free = cm.free_formats(cfg)
    # free run never picks promotion formats (cap must stay deterministic)
    assert set(free) == {"Opinion", "POV", "Signature", "Story", "Comparison", "Method"}


def test_free_formats_fallback_when_matrix_missing():
    cfg = SimpleNamespace()
    assert cm.free_formats(cfg) == ["Opinion", "POV", "Signature", "Story"]


P, PR, PM = "Perspective", "Proof", "Promotion"
A, E, S = "Awareness", "Education", "Selection"
FULL_CFG = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}],
                offers=[{"id": "b"}], magnets=[{"id": "c"}])


def test_pick_target_none_when_matrix_missing():
    assert cm.pick_target_box([(P, A)] * 10, SimpleNamespace()) is None


def test_pick_target_none_below_five_classified():
    assert cm.pick_target_box([(P, A)] * 4, FULL_CFG) is None


def test_partial_window_enforces_only_selection_floor():
    # 6 classified, zero Selection -> floor violated -> a Selection box.
    window = [(P, A), (P, E), (P, A), (PR, A), (P, E), (P, A)]
    target = cm.pick_target_box(window, FULL_CFG)
    assert target is not None and target[1] == S
    # row with the largest deficit that owns a whitelisted Selection box:
    # counts P=5 (target 5, deficit 0), Proof=1 (deficit 2), Promo=0 (deficit 2)
    # tie Proof/Promotion -> fixed order puts Proof first.
    assert target == (PR, S)


def test_partial_window_with_floor_met_returns_none():
    # 6 classified incl. 2 Selection -> floor ok, row quotas not yet enforced.
    window = [(P, S), (PR, S), (P, A), (P, E), (P, A), (P, A)]
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_floor_pick_skips_promotion_when_cap_reached():
    # zero Selection, but already 2 promotion posts -> Promotion x Selection
    # is not a valid floor target; Proof x Selection gated off (no assets).
    cfg = _cfg(boxes=ALL_BOXES)  # 6 effective boxes, only P x S has Selection
    window = [(PM, A), (PM, E), (P, A), (P, E), (P, A), (PR, A),
              (P, A), (P, E), (PR, A), (P, A)]
    assert cm.pick_target_box(window, cfg) == (P, S)


def test_full_window_row_deficit_targets_promotion():
    # P=6, Proof=4, Promo=0 -> Promotion deficient (0 < 2-1). Stage least
    # represented within Promotion boxes; all promo stages at 0 -> order A first.
    window = [(P, A), (P, E), (P, S), (P, A), (P, E), (P, S),
              (PR, A), (PR, E), (PR, A), (PR, E)]
    assert cm.pick_target_box(window, FULL_CFG) == (PM, A)


def test_full_window_balanced_returns_none():
    window = [(P, A), (P, E), (P, S), (P, A), (P, E),
              (PR, A), (PR, E), (PR, S), (PM, A), (PM, E)]
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_full_window_promotion_deficit_blocked_by_cap():
    # Promotion count 2 == cap -> even though Proof fine and P over target,
    # no promotion target may be produced; here nothing else is deficient.
    window = [(P, A), (P, E), (P, S), (P, A), (P, E), (P, S),
              (PR, A), (PR, E), (PM, A), (PM, E)]
    # P=6 (no deficit possible upward), Proof=2 (2 < 3-1 is False), Promo at cap.
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_coverage_line_reports_actuals_vs_targets():
    window = [(P, A)] * 6 + [(PR, E)] * 2 + [(PM, A)] * 2
    line = cm.coverage_line(window, FULL_CFG)
    assert "Perspective 6/5" in line
    assert "Proof 2/3" in line
    assert "Promotion 2/2" in line
    assert "Selection 0/2" in line
