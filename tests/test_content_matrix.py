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
