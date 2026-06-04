"""Tests for format structure injection. Pure functions, no API calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import FORMAT_STRUCTURES, _format_prompts

POST = {"influencer": "Jane Doe", "post_text": "Some source post about pipeline."}


def test_three_formats_defined_with_de_and_en():
    assert set(FORMAT_STRUCTURES) == {"Opinion", "POV", "Signature"}
    for key in FORMAT_STRUCTURES:
        assert FORMAT_STRUCTURES[key]["de"].strip()
        assert FORMAT_STRUCTURES[key]["en"].strip()


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
