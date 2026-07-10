"""Persona-Split lisocon (GTM-Call Jae 2026-07-09): 100% Deutsch, Poster-Routing,
Stimm-Wechsel im DE-Prompt. Jolly bleibt unveraendert (DE+EN, keine Poster-Map)."""
import importlib
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


# --- Poster-Balance (Richard 2026-07-10): gleich viel Content pro Poster -----

_BALANCE_CFG = SimpleNamespace(
    CONTENT_PERSONAS=lisocon.CONTENT_PERSONAS,
    POSTER_BY_PERSONA=lisocon.POSTER_BY_PERSONA,
    POSTER_DEFAULT=lisocon.POSTER_DEFAULT,
    PERSONA_BALANCE_WINDOW=8,
)


def _llm_forbidden():
    c = MagicMock()
    c.messages.create.side_effect = AssertionError("LLM darf bei klarem Rueckstand nicht befragt werden")
    return c


def test_balance_picks_underrepresented_poster():
    recent = ["kaeufer"] * 5 + ["anwender"] * 3  # Reinhard 5, Jae 3
    with patch.object(post_scorer, "client", _llm_forbidden()):
        assert post_scorer.pick_persona(_POST, _BALANCE_CFG, recent)["id"] == "anwender"
    recent = ["anwender"] * 5 + ["kaeufer"] * 3  # Jae 5, Reinhard 3
    with patch.object(post_scorer, "client", _llm_forbidden()):
        assert post_scorer.pick_persona(_POST, _BALANCE_CFG, recent)["id"] == "kaeufer"


def test_balance_overrides_never_twice_rule():
    # Jae ist klar im Rueckstand, obwohl der neueste Eintrag schon anwender war:
    # Aufholen schlaegt die Nie-2x-Regel.
    recent = ["anwender"] + ["kaeufer"] * 6 + ["anwender"]
    with patch.object(post_scorer, "client", _llm_forbidden()):
        assert post_scorer.pick_persona(_POST, _BALANCE_CFG, recent)["id"] == "anwender"


def test_balance_tie_falls_back_to_llm_best_fit():
    resp = MagicMock()
    resp.content = [MagicMock(text="anwender")]
    c = MagicMock()
    c.messages.create.return_value = resp
    recent = ["kaeufer", "anwender"] * 4  # 4:4 -> Best-Fit entscheidet
    with patch.object(post_scorer, "client", c):
        assert post_scorer.pick_persona(_POST, _BALANCE_CFG, recent)["id"] == "anwender"
    assert c.messages.create.called


def test_persona_window_from_config():
    assert post_scorer.persona_window(_BALANCE_CFG) == 8
    assert post_scorer.persona_window(SimpleNamespace()) == 2  # Jolly: nur Nie-2x-Regel


def test_lisocon_has_balance_window_jolly_not():
    assert lisocon.PERSONA_BALANCE_WINDOW == 8
    assert getattr(jolly, "PERSONA_BALANCE_WINDOW", None) is None


def test_dach_prompt_has_german_image_parts():
    # Der DE-Prompt muss Soundbyte/Kontext/Infografik liefern koennen, weil sie
    # bei en_draft=False die Bild-Inputs sind.
    for marker in ("===SOUNDBYTE===", "===KONTEXT===", "===INFOGRAFIK==="):
        assert marker in post_scorer.DACH_POST_PROMPT
