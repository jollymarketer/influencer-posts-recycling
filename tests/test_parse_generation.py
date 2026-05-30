"""Unit tests for the LLM response parser. Pure functions, no API calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import _parse_generation_response


def test_parses_all_four_sections():
    raw = (
        "===POST===\nHook line.\n\n#GTM #RevOps\n"
        "===SOUNDBYTE===\nOne strong line.\n"
        "===KONTEXT===\nCEOs, RevOps\n"
        "===INFOGRAFIK===\nTYP: Eisberg\nMETAPHER: iceberg"
    )
    parts = _parse_generation_response(raw)
    assert parts["post"] == "Hook line.\n\n#GTM #RevOps"
    assert parts["soundbyte"] == "One strong line."
    assert parts["kontext"] == "CEOs, RevOps"
    assert parts["infografik"] == "TYP: Eisberg\nMETAPHER: iceberg"


def test_missing_markers_fall_back_to_raw_post():
    raw = "Just a plain post with no markers."
    parts = _parse_generation_response(raw)
    assert parts["post"] == "Just a plain post with no markers."
    assert parts["soundbyte"] == ""
    assert parts["kontext"] == ""
    assert parts["infografik"] == ""


def test_post_without_kontext_still_parses_soundbyte_and_infografik():
    raw = (
        "===POST===\nBody.\n"
        "===SOUNDBYTE===\nByte.\n"
        "===INFOGRAFIK===\nTYP: Funnel"
    )
    parts = _parse_generation_response(raw)
    assert parts["post"] == "Body."
    assert parts["soundbyte"] == "Byte."
    assert parts["kontext"] == ""
    assert parts["infografik"] == "TYP: Funnel"
