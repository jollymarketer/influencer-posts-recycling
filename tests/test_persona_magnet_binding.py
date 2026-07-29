"""Persona-Bindung der Lead-Magnete, Nutzenachse und InTO-Bruecke.

Kundenfeedback Jae 2026-07-29: ein Anwender-Post trug die Prozess-Diagnose
(Reifegrad-Check, eine Management-Bewertung), und ein Thema zu Terminologie im
Ausgangsdokument kam ohne jeden InTO-Bezug in den Slate.
"""
import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_slate
from tools import content_matrix as cm
from tools import post_scorer

lisocon = importlib.import_module("clients.lisocon.config")

POST = {"influencer": "Jane", "post_text": "Multilingual layout post."}


# --- Client-Config: genau ein Magnet je Persona -----------------------------

def test_lisocon_every_persona_owns_exactly_one_magnet():
    for persona in lisocon.CONTENT_PERSONAS:
        owned = [m for m in lisocon.LEAD_MAGNETS
                 if m.get("persona") == persona["id"]]
        assert len(owned) == 1, persona["id"]


def test_lisocon_magnet_persona_assignment():
    by_id = {m["id"]: m for m in lisocon.LEAD_MAGNETS}
    assert by_id["layout-check"]["persona"] == "anwender"
    assert by_id["prozess-diagnose"]["persona"] == "kaeufer"


def test_lisocon_personas_declare_axis_for_classification():
    assert all(p.get("axis") for p in lisocon.CONTENT_PERSONAS)


# --- Asset-Wahl folgt der Persona ------------------------------------------

def test_asset_for_format_binds_magnet_to_persona():
    anwender = cm.asset_for_format("Magnet", lisocon, [], persona_id="anwender")
    kaeufer = cm.asset_for_format("Magnet", lisocon, [], persona_id="kaeufer")
    assert anwender["id"] == "layout-check"
    assert kaeufer["id"] == "prozess-diagnose"


def test_persona_magnet_survives_lru_pressure():
    """Der Anwender bekommt nie den Kaeufer-Magneten, auch wenn seiner gerade
    erst lief - genau der Fall, der den Reifegrad-Check zu Jae getragen hat."""
    chosen = cm.asset_for_format("Magnet", lisocon, ["layout-check"],
                                 persona_id="anwender")
    assert chosen["id"] == "layout-check"


def test_asset_for_format_without_persona_is_unfiltered():
    assert cm.asset_for_format("Magnet", lisocon, []) is not None


def test_assets_for_persona_keeps_unbound_assets():
    assets = [{"id": "a"}, {"id": "b", "persona": "kaeufer"}]
    assert [a["id"] for a in cm.assets_for_persona(assets, "anwender")] == ["a"]
    assert [a["id"] for a in cm.assets_for_persona(assets, "")] == ["a", "b"]


# --- Magnet-Slots und Deckungs-Guard ---------------------------------------

_CFG_ONE_SIDED = SimpleNamespace(
    LEAD_MAGNETS=[{"id": "m1", "persona": "kaeufer"}],
    MAGNET_SLOTS_PER_SLATE=2,
    CONTENT_PERSONAS=[{"id": "kaeufer"}, {"id": "anwender"}],
)


def _slate(personas):
    return [{"post_url": f"u{i}", "persona": p} for i, p in enumerate(personas)]


def test_magnet_slot_skipped_for_persona_without_magnet():
    slate = _slate(["kaeufer"] * 3 + ["anwender"] * 3)
    slots = run_slate.pick_magnet_slots(slate, _CFG_ONE_SIDED)
    assert len(slots) == 1
    assert all(slate[i]["persona"] == "kaeufer" for i in slots)


def test_magnet_slot_per_persona_when_both_covered():
    slate = _slate(["kaeufer"] * 3 + ["anwender"] * 3)
    slots = run_slate.pick_magnet_slots(slate, lisocon)
    assert len(slots) == 2
    assert {slate[i]["persona"] for i in slots} == {"kaeufer", "anwender"}


def test_check_magnet_coverage_names_uncovered_persona():
    assert run_slate.check_magnet_coverage(_CFG_ONE_SIDED) == ["anwender"]
    assert run_slate.check_magnet_coverage(lisocon) == []


# --- InTO-Bruecke ----------------------------------------------------------

def test_drop_without_bridge_splits_candidates():
    scored = [{"post_url": "a", "into_bridge": "landet im Fremdsprachensatz"},
              {"post_url": "b", "into_bridge": ""},
              {"post_url": "c", "into_bridge": "   "}]
    keep, dropped = run_slate.drop_without_bridge(scored, lisocon)
    assert [c["post_url"] for c in keep] == ["a"]
    assert [c["post_url"] for c in dropped] == ["b", "c"]


def test_drop_without_bridge_is_noop_without_config():
    scored = [{"post_url": "a", "into_bridge": ""}]
    keep, dropped = run_slate.drop_without_bridge(scored, SimpleNamespace())
    assert keep == scored and dropped == []


def test_classify_section_carries_axis_menu_and_bridge():
    cfg = SimpleNamespace(
        CONTENT_PERSONAS=[{"id": "kaeufer", "axis": "Kosten des Gesamtprozesses"},
                          {"id": "anwender", "axis": "Muehe der Layout-Arbeit"}],
        CLASSIFY_BRIDGE="Wie landet der Winkel nach der Uebersetzung?",
    )
    with patch.object(post_scorer, "_cfg", cfg):
        section = post_scorer._classify_section()
    assert "kaeufer: Kosten des Gesamtprozesses" in section
    assert "anwender: Muehe der Layout-Arbeit" in section
    assert "into_bridge" in section
    # Der Winkel wird vor der Persona erhoben: er entscheidet die Achse.
    assert section.index("topic_angle_de") < section.index('"persona"')


def test_classify_section_without_bridge_config():
    cfg = SimpleNamespace(CONTENT_PERSONAS=[{"id": "kaeufer", "axis": "Kosten"}])
    with patch.object(post_scorer, "_cfg", cfg):
        assert "into_bridge" not in post_scorer._classify_section()


# --- Nutzenachse und persona-abhaengige Prompt-Tokens ----------------------

def test_persona_block_renders_value_axis_only_when_present():
    with_axis = post_scorer.persona_block(
        {"label": "Anwender", "value_axis": "weniger Handarbeit"}, "de")
    without = post_scorer.persona_block({"label": "Kaeufer"}, "de")
    assert "weniger Handarbeit" in with_axis
    assert "aufloest" not in without


def test_lisocon_anwender_forbids_maturity_framing():
    anwender = next(p for p in lisocon.CONTENT_PERSONAS if p["id"] == "anwender")
    assert "Reifegrad" in anwender["vocabulary_avoid"]
    assert anwender["value_axis"]


def test_persona_prompt_tokens_override_and_fallback():
    override = post_scorer.persona_prompt_tokens({"audience_de": "Nur DTP-Leute."})
    fallback = post_scorer.persona_prompt_tokens(None)
    assert override["audience_de"] == "Nur DTP-Leute."
    assert override["focus_topics_de"] == post_scorer._cfg.TOKENS["FOCUS_TOPICS_DE"]
    assert fallback["audience_de"] == post_scorer._cfg.TOKENS["AUDIENCE_DE"]


def test_format_prompts_use_persona_audience_instead_of_static_token():
    tokens = post_scorer.persona_prompt_tokens({
        "audience_de": "Nur DTP-Leute.",
        "decision_makers_de": "Praktiker, nicht Budget-Entscheider",
        "focus_topics_de": "Handgriffe pro Sprachversion",
    })
    de, _ = post_scorer._format_prompts(POST, persona_tokens_de=tokens)
    assert "Nur DTP-Leute." in de
    assert "Praktiker, nicht Budget-Entscheider" in de
    assert "Handgriffe pro Sprachversion" in de
    assert post_scorer._cfg.TOKENS["AUDIENCE_DE"] not in de


def test_format_prompts_fall_back_to_static_tokens():
    de, _ = post_scorer._format_prompts(POST)
    assert post_scorer._cfg.TOKENS["AUDIENCE_DE"] in de
