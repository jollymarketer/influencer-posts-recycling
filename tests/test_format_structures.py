"""Tests for format structure injection. Pure functions, no API calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import FORMAT_STRUCTURES, _format_prompts

POST = {"influencer": "Jane Doe", "post_text": "Some source post about pipeline."}


ALL_FORMAT_KEYS = {"Opinion", "POV", "Signature", "Story",
                   "Comparison", "Method", "CaseProof", "Debate", "Magnet", "Offer"}


def test_formats_defined_with_de_and_en():
    assert set(FORMAT_STRUCTURES) == ALL_FORMAT_KEYS
    for key in FORMAT_STRUCTURES:
        assert FORMAT_STRUCTURES[key]["de"].strip()
        assert FORMAT_STRUCTURES[key]["en"].strip()


def test_story_injects_narrative_structure():
    de, en = _format_prompts(POST, "Story")
    assert "Szene" in de
    assert "narrative" in en.lower()


def test_opinion_injects_contrarian_structure():
    de, en = _format_prompts(POST, "Opinion")
    assert "Gegenposition" in de
    assert "contrarian" in en.lower()


def test_pov_injects_framework_structure():
    de, en = _format_prompts(POST, "POV")
    assert "Denk-Linse" in de
    assert "lens" in en.lower()


def test_signature_injects_belief_vs_reality_structure():
    de, en = _format_prompts(POST, "Signature")
    assert "glauben" in de.lower()
    assert "Vergleichstabelle" in de
    assert "belief" in en.lower()


def test_unknown_format_falls_back_to_opinion():
    de_known, _ = _format_prompts(POST, "Opinion")
    de_unknown, _ = _format_prompts(POST, "Nonsense")
    assert "Gegenposition" in de_unknown  # same as Opinion block


def test_post_text_and_influencer_present_in_prompt():
    de, en = _format_prompts(POST, "POV")
    assert "Jane Doe" in de and "Jane Doe" in en
    assert "Some source post" in de and "Some source post" in en


from unittest.mock import MagicMock, patch


def test_generate_threads_format_into_de_prompt():
    captured = []

    def fake_create(**kw):
        captured.append(kw["messages"][0]["content"])
        resp = MagicMock()
        resp.content = [MagicMock(text="===POST===\nBody.\n===SOUNDBYTE===\nByte.")]
        return resp

    with patch("tools.post_scorer.client") as c:
        c.messages.create.side_effect = fake_create
        from tools.post_scorer import generate_post_and_image_prompt
        generate_post_and_image_prompt(POST, "Signature")

    # First call is the DE prompt; it must carry the Signature structure.
    assert "Vergleichstabelle" in captured[0]


def test_comparison_injects_decision_structure():
    de, en = _format_prompts(POST, "Comparison")
    assert "Entscheidungskriterien" in de and "Red Flags" in de
    assert "red flags" in en.lower()
    assert "Kein DM-CTA" in de  # promotion ban stays outside promotion row


def test_method_injects_steps_and_pitfall():
    de, en = _format_prompts(POST, "Method")
    assert "Stolperstein" in de
    assert "pitfall" in en.lower()


def test_caseproof_pins_numbers_to_asset():
    de, en = _format_prompts(POST, "CaseProof")
    assert "CASE-ASSET" in de and "woertlich" in de
    assert "case asset" in en.lower() and "verbatim" in en.lower()


def test_debate_demands_reply_not_dm():
    de, en = _format_prompts(POST, "Debate")
    assert "Lager" in de and "Kein DM-CTA" in de
    assert "camp" in en.lower()


def test_magnet_allows_exactly_comment_cta():
    de, en = _format_prompts(POST, "Magnet")
    assert "Kommentar-CTA" in de and "LEAD-MAGNET-ASSET" in de
    assert "comment" in en.lower()


def test_offer_allows_dm_or_discovery_cta_without_scarcity():
    de, en = _format_prompts(POST, "Offer")
    assert "OFFER-ASSET" in de and "Kein kuenstlicher Zeitdruck" in de
    assert "scarcity" in en.lower()
