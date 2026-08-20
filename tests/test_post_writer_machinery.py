"""Tests fuer den Themen-Pfad durch die volle DACH-Prompt-Maschinerie.
Kein Modellaufruf."""
import importlib
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps
from tools import post_writer as pw

swot = importlib.import_module("clients.swot.config")


# --- Template-Chirurgie ------------------------------------------------------

def test_topic_template_is_reframed():
    t = pw.TOPIC_DE_TEMPLATE
    assert "THEMEN-MATERIAL:" in t
    assert "Recycel den folgenden LinkedIn-Post" not in t
    assert "ORIGINAL POST:" not in t
    assert "den der Quell-Post nicht hat" not in t


def test_topic_template_keeps_enforcement_blocks():
    t = pw.TOPIC_DE_TEMPLATE
    assert "Qualitaetspruefung (E3)" in t
    assert "===SOUNDBYTE===" in t
    assert "===INFOGRAFIK===" in t
    assert "{structure_block}" in t
    assert "{length_target_de}" in t


def test_format_prompts_accepts_template_override():
    post = {"influencer": "X", "post_text": "Quelltext"}
    custom = ps.DACH_POST_PROMPT.replace("TEIL 1", "XX-MARKER-TEIL 1")
    de, _ = ps._format_prompts(post, "Opinion", de_template=custom)
    assert "XX-MARKER-TEIL 1" in de
    de_default, _ = ps._format_prompts(post, "Opinion")
    assert "XX-MARKER-TEIL 1" not in de_default


# --- Prompt-Bau --------------------------------------------------------------

def test_build_prompt_injects_voice_persona_and_material():
    p = pw.build_prompt("Titel A", "Herkunft B", "LinkedIn Robert",
                        "excel_am_limit", post_format="Opinion", cfg=swot)
    assert "Robert Werner" in p                      # Kontostimme
    assert "Titel A" in p and "Herkunft B" in p      # Themen-Material
    persona = {x["id"]: x for x in swot.CONTENT_PERSONAS}["excel_am_limit"]
    assert persona["pains"].split(";")[0] in p       # Persona-Block
    assert persona["audience_de"][:40] in p          # Persona-Token-Override


def test_build_prompt_story_gets_long_target():
    p = pw.build_prompt("T", "K", "LinkedIn Robert", "fristen",
                        post_format="Story", cfg=swot)
    assert "350-400" in p


def test_build_prompt_unknown_channel_raises():
    with pytest.raises(KeyError, match="LinkedIn Falsch"):
        pw.build_prompt("T", "K", "LinkedIn Falsch", "fristen", cfg=swot)


# --- write_post Pipeline -----------------------------------------------------

def test_write_post_delegates_with_topic_template():
    with patch.object(pw, "generate_post_and_image_prompt",
                      return_value=("TEXT", "", "IMG", "TYP: Waage", "SB", "CEO")) as gen:
        out = pw.write_post("Titel A", "Herkunft B", "LinkedIn Robert",
                            "excel_am_limit", post_format="POV", cfg=swot)
    kwargs = gen.call_args.kwargs
    assert kwargs["de_template"] is pw.TOPIC_DE_TEMPLATE
    assert "Titel A" in gen.call_args.args[0]["post_text"]
    assert gen.call_args.args[1] == "POV"
    assert kwargs["persona_voice_de"] == swot.ACCOUNT_VOICES["LinkedIn Robert"]
    assert out == {"text": "TEXT", "soundbyte": "SB", "kontext": "CEO",
                   "skeleton": "TYP: Waage"}
