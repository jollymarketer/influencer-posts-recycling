"""CaseProof im Plan-Fill: Vorgeschichte, Beleg-Rotation, Ziel-Box.
Kein Notion-, kein Modellaufruf."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_plan_fill

ASSETS = [
    {"id": "a1", "metric": "35% weniger Aufwand"},
    {"id": "a2", "metric": "von zwei Tagen auf einen"},
    {"id": "a3", "metric": "90% weniger Nacharbeit"},
]

MATRIX = {
    "mix": {"Perspective": 6, "Proof": 4, "Promotion": 0},
    "selection_floor": 2,
    "promotion_cap": 0,
    "boxes": [("Perspective", "Awareness"), ("Perspective", "Education"),
              ("Proof", "Awareness"), ("Proof", "Selection")],
}

CFG = SimpleNamespace(MATRIX=MATRIX, PROOF_ASSETS=ASSETS)
# Zehn Beitraege ohne einen einzigen Selection-Post: der Floor ist offen.
OHNE_SELECTION = ["Opinion", "POV", "Signature", "Story"] * 3


def _row(fmt, kanal="LinkedIn Christian", tag="2026-09-01"):
    props = {"Kanal": {"select": {"name": kanal}},
             "Geplant für": {"date": {"start": tag}}}
    if fmt:
        props["Format"] = {"select": {"name": fmt}}
    return {"properties": props}


def test_format_history_newest_first_per_kanal():
    rows = [_row("Opinion", tag="2026-09-01"),
            _row("Story", tag="2026-09-03"),
            _row("POV", kanal="LinkedIn Robert", tag="2026-09-02")]
    hist = run_plan_fill._format_history(rows)
    assert hist["LinkedIn Christian"] == ["Story", "Opinion"]
    assert hist["LinkedIn Robert"] == ["POV"]


def test_format_history_skips_rows_without_format():
    hist = run_plan_fill._format_history([_row(None), _row("Opinion")])
    assert hist["LinkedIn Christian"] == ["Opinion"]


def test_asset_history_cycles_through_all_assets():
    assert run_plan_fill._asset_history([], CFG) == []
    assert run_plan_fill._asset_history([_row("CaseProof")], CFG) == ["a1"]
    assert run_plan_fill._asset_history([_row("CaseProof")] * 2, CFG) == ["a2", "a1"]
    # Nach einer vollen Runde faengt der Zyklus wieder vorne an.
    assert run_plan_fill._asset_history([_row("CaseProof")] * 3, CFG) == []


def test_asset_history_empty_without_proof_assets():
    leer = SimpleNamespace(MATRIX=MATRIX, PROOF_ASSETS=[])
    assert run_plan_fill._asset_history([_row("CaseProof")], leer) == []


def test_offener_selection_floor_erzwingt_caseproof_mit_beleg():
    with patch.object(run_plan_fill, "pick_format") as mock_pick:
        mock_pick.side_effect = lambda post, recent, cands: cands[0]
        fmt, asset = run_plan_fill._choose_format(CFG, "Material", OHNE_SELECTION, [])
    assert fmt == "CaseProof"
    assert asset["id"] == "a1"
    # Die Pflicht-Box laesst genau einen Kandidaten zu.
    assert mock_pick.call_args.args[2] == ["CaseProof"]


def test_caseproof_nie_aus_dem_freien_pool():
    """Ohne Ziel-Box (leere Vorgeschichte) bleiben nur die vier freien
    Formate: ein Asset-Format darf nie ueber den Free-Fill kommen."""
    with patch.object(run_plan_fill, "pick_format") as mock_pick:
        mock_pick.side_effect = lambda post, recent, cands: cands[0]
        fmt, asset = run_plan_fill._choose_format(CFG, "Material", [], [])
    assert mock_pick.call_args.args[2] == ["Opinion", "POV", "Signature", "Story"]
    assert fmt != "CaseProof"
    assert asset is None


def test_ohne_proof_assets_faellt_die_box_weg():
    """Leerer Asset-Block schliesst die Box: sonst forderte der Prompt eine
    Zahlenquelle, die es nicht gibt."""
    leer = SimpleNamespace(MATRIX=MATRIX, PROOF_ASSETS=[])
    with patch.object(run_plan_fill, "pick_format") as mock_pick:
        mock_pick.side_effect = lambda post, recent, cands: cands[0]
        fmt, asset = run_plan_fill._choose_format(leer, "Material", OHNE_SELECTION, [])
    assert fmt != "CaseProof"
    assert asset is None
