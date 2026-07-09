"""Persona-Split lisocon (GTM-Call Jae 2026-07-09): 100% Deutsch, Poster-Routing,
Stimm-Wechsel im DE-Prompt. Jolly bleibt unveraendert (DE+EN, keine Poster-Map)."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")

_POST = {"influencer": "Test Person", "post_text": "Ein Test-Post ueber Terminologie."}


def test_lisocon_is_german_only():
    assert lisocon.FEATURES["en_draft"] is False
    assert lisocon.FEATURES["grammar_check"] is True
    assert lisocon.IMAGE_LANGUAGE == "German"


def test_jolly_defaults_unchanged():
    assert jolly.FEATURES.get("en_draft", True) is True
    assert not jolly.FEATURES.get("grammar_check")
    assert getattr(jolly, "POSTER_BY_PERSONA", None) is None
    assert getattr(jolly, "IMAGE_LANGUAGE", "English") == "English"


def test_lisocon_poster_map_and_voice():
    assert lisocon.POSTER_BY_PERSONA == {"kaeufer": "Reinhard", "anwender": "Jae"}
    assert lisocon.POSTER_DEFAULT == "Reinhard"
    anwender = next(p for p in lisocon.CONTENT_PERSONAS if p["id"] == "anwender")
    assert "Jae Hyun Kim" in anwender["voice_de"]
    kaeufer = next(p for p in lisocon.CONTENT_PERSONAS if p["id"] == "kaeufer")
    assert "voice_de" not in kaeufer  # Default-Stimme (PERSONA_DE) bleibt


def test_format_prompts_default_voice_is_persona_de_token():
    de, _ = post_scorer._format_prompts(_POST)
    assert de.startswith(post_scorer._cfg.TOKENS["PERSONA_DE"])


def test_format_prompts_voice_override_replaces_author():
    voice = "Du bist Test-Autor Nummer Zwei."
    de, _ = post_scorer._format_prompts(_POST, persona_voice_de=voice)
    assert de.startswith(voice)
    assert post_scorer._cfg.TOKENS["PERSONA_DE"] not in de


def test_dach_prompt_has_german_image_parts():
    # Der DE-Prompt muss Soundbyte/Kontext/Infografik liefern koennen, weil sie
    # bei en_draft=False die Bild-Inputs sind.
    for marker in ("===SOUNDBYTE===", "===KONTEXT===", "===INFOGRAFIK==="):
        assert marker in post_scorer.DACH_POST_PROMPT
