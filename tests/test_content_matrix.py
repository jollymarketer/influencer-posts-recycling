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


def test_row_deficit_promotion_blocked_by_cap_with_custom_mix():
    # Mix verlangt 4 Promotion-Posts, Kappe erlaubt nur 2: Promotion ist
    # defizitaer (2 < 4-1), aber die Kappe blockt das Ziel -> None
    # (keine andere Zeile defizitaer: P=5 >= 5-1, Proof=3 >= 3-1).
    cfg = _cfg(boxes=ALL_BOXES, proof=[{"id": "a"}], offers=[{"id": "b"}],
               magnets=[{"id": "c"}], mix={"Perspective": 5, "Proof": 3, "Promotion": 4})
    window = [(P, A), (P, E), (P, S), (P, A), (P, E),
              (PR, A), (PR, E), (PR, S), (PM, A), (PM, E)]
    assert cm.pick_target_box(window, cfg) is None


def test_row_deficit_tie_breaks_in_jobs_order():
    # Proof und Promotion beide Defizit 2 -> feste JOBS-Ordnung waehlt Proof.
    window = [(P, A), (P, E), (P, S), (P, A), (P, E),
              (P, S), (P, A), (P, E), (P, A), (PR, A)]
    # P=9, Proof=1 (1 < 2 defizitaer), Promotion=0 (0 < 1 defizitaer); Tie bei Defizit 2.
    target = cm.pick_target_box(window, FULL_CFG)
    assert target[0] == PR


def test_unclassified_entries_do_not_shrink_the_window():
    # 5 unklassifizierte Eintraege vor 10 sauberen: Fenster bleibt 10,
    # volle Zeilen-Logik greift (Promotion 0 -> defizitaer -> (PM, A)).
    noise = [("Unbekannt", "X")] * 5
    clean = [(P, A), (P, E), (P, S), (P, A), (P, E), (P, S),
             (PR, A), (PR, E), (PR, A), (PR, E)]
    assert cm.pick_target_box(noise + clean, FULL_CFG) == (PM, A)


def test_row_at_exactly_mix_minus_one_is_not_deficient():
    # Proof genau bei mix-1 (2 von Soll 3): unter Soll, aber nicht um einen
    # vollen Post -> nicht defizitaer -> None.
    window = [(P, A), (P, E), (P, S), (P, A), (P, E), (P, S),
              (PR, A), (PR, E), (PM, A), (PM, E)]
    assert cm.pick_target_box(window, FULL_CFG) is None


def test_coverage_line_reports_actuals_vs_targets():
    window = [(P, A)] * 6 + [(PR, E)] * 2 + [(PM, A)] * 2
    line = cm.coverage_line(window, FULL_CFG)
    assert "Perspective 6/5" in line
    assert "Proof 2/3" in line
    assert "Promotion 2/2" in line
    assert "Selection 0/2" in line
