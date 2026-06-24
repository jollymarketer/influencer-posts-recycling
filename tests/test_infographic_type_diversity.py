"""Tests for the infographic-type diversity feature: parse/normalize helpers,
the anti-repeat line injection into _format_prompts (also guards the prompt
.format() placeholders), build_infographic_prompt passing new layouts through,
and get_recent_infographic_types parsing. No API calls."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer
from tools import notion_db

POST = {"influencer": "Jane", "post_text": "A post about a trade-off between speed and quality."}


# --- parse_infographic_type ---------------------------------------------------

def test_parse_infographic_type_extracts_typ():
    sk = "TYP: 2x2 matrix\nMETAPHER: none\nEBENEN:\nA: x, y"
    assert post_scorer.parse_infographic_type(sk) == "2x2 matrix"


def test_parse_infographic_type_empty_when_absent():
    assert post_scorer.parse_infographic_type("EBENEN:\nA: x") == ""
    assert post_scorer.parse_infographic_type("") == ""


# --- normalize_infographic_type -----------------------------------------------

def test_normalize_maps_german_and_english_variants():
    assert post_scorer.normalize_infographic_type("Eisberg") == "Iceberg"
    assert post_scorer.normalize_infographic_type("a 2x2 quadrant chart") == "2x2 matrix"
    assert post_scorer.normalize_infographic_type("Waage/Hebel") == "Scale/seesaw"
    assert post_scorer.normalize_infographic_type("Flywheel loop") == "Flywheel/loop"


def test_normalize_unknown_returns_raw_capped():
    assert post_scorer.normalize_infographic_type("some bespoke spiral") == "some bespoke spiral"
    assert post_scorer.normalize_infographic_type("") == ""


# --- anti-repeat line injection (guards prompt .format placeholders) ----------

def test_format_prompts_injects_recent_types_into_both_languages():
    de, en = post_scorer._format_prompts(POST, "Opinion", ["Iceberg", "Funnel/pyramid"])
    assert "Iceberg, Funnel/pyramid" in de and "letzten 3 Runs" in de
    assert "Iceberg, Funnel/pyramid" in en and "last 3 runs" in en


def test_format_prompts_no_recent_types_still_formats_cleanly():
    # Must not raise KeyError (placeholder present) and must not leave a stray bullet.
    de, en = post_scorer._format_prompts(POST, "Opinion", [])
    assert "{recent_types_line}" not in de and "{recent_types_line}" not in en
    assert "newest first" not in en and "Zuletzt genutzte Typen" not in de


def test_recent_types_lines_filters_empties():
    de, en = post_scorer._recent_types_lines([None, "", "Iceberg"])
    assert "Iceberg" in de and "Iceberg" in en
    assert post_scorer._recent_types_lines([]) == ("", "")


# --- build_infographic_prompt passes new layout types through -----------------

def test_build_infographic_prompt_carries_new_layout_type():
    sk = ("TYP: 2x2 matrix\nMETAPHER: none\nEBENEN:\n"
          "High impact: quick wins\nLow impact: time sinks")
    prompt = post_scorer.build_infographic_prompt(sk, language="English")
    assert "Layout style: 2x2 matrix" in prompt
    assert "quick wins" in prompt


# --- get_recent_infographic_types parsing -------------------------------------

def test_get_recent_infographic_types_reads_select(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "results": [
            {"properties": {"Infografik-Typ": {"select": {"name": "Iceberg"}}}},
            {"properties": {"Infografik-Typ": {"select": {"name": "Scale/seesaw"}}}},
            {"properties": {"Infografik-Typ": {"select": None}}},  # tolerated
        ]
    }
    with patch.object(notion_db, "_notion_request", return_value=resp):
        out = notion_db.get_recent_infographic_types()
    assert out == ["Iceberg", "Scale/seesaw"]
