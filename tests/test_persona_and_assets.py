"""Persona lens + asset injection into the generation prompts. Client mocked."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

POST = {"influencer": "Jane", "post_text": "Pipeline predictability post."}
PERSONAS = [
    {"id": "founder-ceo", "label": "Founder / CEO", "share": "dominant",
     "pains": "Pipeline nicht planbar", "kpis": "Meetings/Monat",
     "vocabulary_use": "Planbarkeit", "vocabulary_avoid": "MQL",
     "scene_de": "ein Founder im leeren Pipeline-Monat",
     "scene_en": "a founder in an empty-pipeline month", "cta_style": "discovery"},
    {"id": "cro-vp-sales", "label": "CRO / VP Sales", "share": "secondary",
     "pains": "Quote verfehlt", "kpis": "Coverage",
     "vocabulary_use": "Coverage", "vocabulary_avoid": "Brand-Sprech",
     "scene_de": "ein VP Sales im Forecast-Call",
     "scene_en": "a VP of sales in a forecast call", "cta_style": "discovery"},
]
CFG = SimpleNamespace(CONTENT_PERSONAS=PERSONAS)


def _mock(reply):
    resp = MagicMock()
    resp.content = [MagicMock(text=reply)]
    c = MagicMock()
    c.messages.create.return_value = resp
    return c


def test_pick_persona_none_without_personas():
    assert post_scorer.pick_persona(POST, SimpleNamespace(), []) is None
    assert post_scorer.pick_persona(POST, SimpleNamespace(CONTENT_PERSONAS=[]), []) is None


def test_pick_persona_llm_choice():
    with patch.object(post_scorer, "client", _mock("cro-vp-sales")):
        assert post_scorer.pick_persona(POST, CFG, [])["id"] == "cro-vp-sales"


def test_pick_persona_secondary_never_twice_in_a_row():
    with patch.object(post_scorer, "client", _mock("cro-vp-sales")):
        chosen = post_scorer.pick_persona(POST, CFG, ["cro-vp-sales"])
    assert chosen["id"] == "founder-ceo"  # falls back to dominant


def test_pick_persona_api_error_returns_dominant():
    c = MagicMock()
    c.messages.create.side_effect = RuntimeError("down")
    with patch.object(post_scorer, "client", c):
        assert post_scorer.pick_persona(POST, CFG, [])["id"] == "founder-ceo"


def test_persona_block_renders_language_specific_scene():
    de = post_scorer.persona_block(PERSONAS[0], "de")
    en = post_scorer.persona_block(PERSONAS[0], "en")
    assert "ZIEL-PERSONA" in de and "leeren Pipeline-Monat" in de
    assert "TARGET PERSONA" in en and "empty-pipeline month" in en
    assert post_scorer.persona_block(None, "de") == ""


def test_assets_block_caseproof_pins_metric():
    asset = {"id": "case-a", "claim": "Outbound-System", "metric": "12 Meetings in 6 Wochen",
             "context": "freigegeben"}
    de = post_scorer.assets_block("CaseProof", asset, "de")
    en = post_scorer.assets_block("CaseProof", asset, "en")
    assert "CASE-ASSET" in de and "12 Meetings in 6 Wochen" in de
    assert "CASE ASSET" in en
    assert post_scorer.assets_block("CaseProof", None, "de") == ""
    assert post_scorer.assets_block("Opinion", asset, "de") == ""


def test_format_prompts_inject_persona_and_assets():
    asset = {"id": "case-a", "metric": "12 Meetings in 6 Wochen"}
    de, en = post_scorer._format_prompts(
        POST, "CaseProof",
        assets_de=post_scorer.assets_block("CaseProof", asset, "de"),
        assets_en=post_scorer.assets_block("CaseProof", asset, "en"),
        persona_de=post_scorer.persona_block(PERSONAS[0], "de"),
        persona_en=post_scorer.persona_block(PERSONAS[0], "en"),
    )
    assert "12 Meetings in 6 Wochen" in de and "ZIEL-PERSONA" in de
    assert "12 Meetings in 6 Wochen" in en and "TARGET PERSONA" in en


def test_format_prompts_default_empty_blocks():
    de, en = post_scorer._format_prompts(POST, "Opinion")
    assert "ZIEL-PERSONA" not in de and "CASE-ASSET" not in de
