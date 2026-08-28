"""Infografik-Split: Soundbyte, Kontext und Skelett kommen ohne EN-Draft aus
einem eigenen Haiku-Call nach dem Text, nie mehr aus dem Schreib-Prompt."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps

POST = {"influencer": "Test", "post_text": "Some source post", "likes": 1, "comments": 0, "shares": 0}
PARTS = "===SOUNDBYTE===\nEin Satz.\n===KONTEXT===\nCFOs\n===INFOGRAFIK===\nTYP: Waage\nMETAPHER: keine"


def test_de_prompt_has_no_parts_sections_and_ends_with_post_marker():
    de, _ = ps._format_prompts(POST, "Opinion")
    assert "TEIL 2 - SOUND BYTE" not in de and "INFOGRAFIK-TYPEN" not in de
    assert "===SOUNDBYTE===" not in de
    assert de.rstrip().endswith("===POST===\n[LinkedIn-Post-Text auf Deutsch]")


def test_parts_prompt_carries_post_types_and_recent_line():
    p = ps.PARTS_PROMPT.format(post="Der Beitrag.", recent_types_line="- Zuletzt genutzte Typen: Iceberg.")
    assert "Der Beitrag." in p and "INFOGRAFIK-TYPEN" in p and "Zuletzt genutzte Typen" in p
    assert "===POST===" not in p and "===SOUNDBYTE===" in p


def test_without_en_draft_parts_come_from_second_call():
    calls = []

    def fake_create(**kw):
        calls.append((kw["model"], kw["messages"][0]["content"]))
        resp = MagicMock()
        resp.content = [MagicMock(text=PARTS if "BEITRAG:" in kw["messages"][0]["content"]
                                  else "===POST===\nBody.")]
        return resp

    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False, "en_draft": False,
                                       "naturalness_check": False}):
        c.messages.create.side_effect = fake_create
        de, en, img, skeleton, sound, kontext = ps.generate_post_and_image_prompt(POST, "Opinion")
    # startswith: blanket_cta haengt je nach Prozess-Mandant einen CTA an.
    assert de.startswith("Body.") and en == ""
    assert sound == "Ein Satz." and kontext == "CFOs" and skeleton.startswith("TYP: Waage")
    assert [m for m, _ in calls] == ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
    assert "Body." in calls[1][1]


def test_with_en_draft_no_parts_call():
    calls = []

    def fake_create(**kw):
        calls.append(kw["model"])
        resp = MagicMock()
        resp.content = [MagicMock(text="===POST===\nBody.\n===SOUNDBYTE===\nByte.")]
        return resp

    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False, "en_draft": True,
                                       "naturalness_check": False}):
        c.messages.create.side_effect = fake_create
        de, en, *_ = ps.generate_post_and_image_prompt(POST, "Opinion")
    assert calls == ["claude-sonnet-4-6", "claude-sonnet-4-6"]
    assert en.startswith("Body.")


def test_parts_call_failure_returns_empty_parts():
    with patch("tools.post_scorer.client") as c:
        c.messages.create.side_effect = RuntimeError("down")
        parts = ps._parts_call("Text")
    assert parts == {"post": "", "soundbyte": "", "kontext": "", "infografik": ""}


def test_generic_line_carries_no_spelled_out_formulas():
    assert "kein X-Problem" not in ps.DACH_POST_PROMPT
    assert "Nicht X. Nicht Y." not in ps.DACH_POST_PROMPT
    assert "Uebergabefaehigkeit" not in ps.DACH_POST_PROMPT
    assert "Keine rhetorischen Schablonen" in ps.DACH_POST_PROMPT
