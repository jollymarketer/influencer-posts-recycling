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
    assert "===POST===" in t
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
    assert "1.600-2.000 Zeichen" in p


def test_build_prompt_short_format_gets_capped_target():
    # Kurzformate deckeln im Engagement-Band (Richard, 21.08.2026); die ersten
    # 200 Zeichen tragen die These, dort schneidet LinkedIn ab.
    p = pw.build_prompt("T", "K", "LinkedIn Robert", "fristen",
                        post_format="Opinion", cfg=swot)
    assert "1.200-1.600 Zeichen" in p
    assert "ersten 200 Zeichen" in p


def test_voice_profiles_are_loaded_into_account_voices():
    # Stimmprofile aus clients/swot/voices/*.md (25.08.2026). Fehlt eine
    # Datei, bleibt die Rollenbeschreibung, nichts bricht.
    assert swot.load_voice_profile("gibt_es_nicht") == ""
    for name, kanal in (("werner", "LinkedIn Robert"), ("kulle", "LinkedIn Christian")):
        profile = swot.load_voice_profile(name)
        if profile:
            assert "STIMMPROFIL" in swot.ACCOUNT_VOICES[kanal]
            assert "## Typische Wendungen" in profile


def test_build_prompt_carries_publication_date():
    p = pw.build_prompt("T", "K", "LinkedIn Robert", "fristen", cfg=swot, datum="2026-09-10")
    assert "Erscheinungsdatum des Beitrags: 2026-09-10" in p
    assert "Erscheinungsdatum" not in pw.build_prompt("T", "K", "LinkedIn Robert", "fristen", cfg=swot)


def test_build_prompt_appends_avoid_phrases():
    p = pw.build_prompt("T", "K", "LinkedIn Robert", "fristen", cfg=swot,
                        avoid_phrases=["In Einführungsprojekten sehe ich"])
    assert "SCHON VERBRAUCHT" in p and "In Einführungsprojekten sehe ich" in p
    assert "SCHON VERBRAUCHT" not in pw.build_prompt("T", "K", "LinkedIn Robert", "fristen", cfg=swot)


def test_build_prompt_kurz_band_uses_short_form():
    p = pw.build_prompt("T", "K", "LinkedIn Robert", "fristen",
                        post_format="Story", cfg=swot, band="kurz")
    assert "Kurzform" in p and "500-900 Zeichen" in p


def test_build_prompt_carries_hersteller_position_and_bans():
    # Kulle 24.08.2026: Softwarehersteller-Perspektive, keine Bankgespraech-
    # Ich-Form, Gesetze erklaeren, "Glaube" raus.
    # Die Kontostimme kommt ueber cfg in den Prompt; die TOKENS backt das
    # Template beim Import mit dem Prozess-Mandanten, deshalb direkt geprueft.
    p = pw.build_prompt("T", "K", "LinkedIn Christian", "rechenschaft", cfg=swot)
    assert "kein Interim-CFO" in p
    # 02.09.2026 (Inga Baumert 01.09.: "zu sachlich"): genau eine
    # Ich-Beobachtung je Beitrag, wechselnde Situation, direkte Ansprache am
    # Schluss. Kein fertiger Satzbaustein wie "In Einfuehrungsprojekten sehe ich".
    assert "Genau eine Beobachtung je Beitrag in der Ich-Form" in p
    assert "sehe ich" not in p
    assert "sprichst du den Leser direkt an" in p
    assert "Grossbuchstaben" in p                 # globales Template
    assert "StaRUG, IFRS 18, AVR, InsO" in swot.TOKENS["CONTEXT_TRANSFER_DE"]
    assert "Glaube" not in swot.TOKENS["LANGUAGE_BANS_DE"]      # 28.08.2026: Zeile raus, der Leser faengt es
    assert "Praemisse" not in swot.TOKENS["LANGUAGE_BANS_DE"]
    assert "Bankgespraechs" in swot.TOKENS["LANGUAGE_BANS_DE"]


def test_length_band_rotation_per_channel():
    assert [pw.length_band_for(swot, i) for i in range(6)] == \
        ["standard", "standard", "kurz", "standard", "standard", "kurz"]

    class NoRotation:
        pass
    assert pw.length_band_for(NoRotation(), 2) is None
    # 02.09.2026: Christian jeder zweite kurz, Robert bleibt bei jedem dritten.
    assert [pw.length_band_for(swot, i, "LinkedIn Christian") for i in range(4)] == \
        ["standard", "kurz", "standard", "kurz"]
    assert [pw.length_band_for(swot, i, "LinkedIn Robert") for i in range(3)] == \
        ["standard", "standard", "kurz"]


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
    assert kwargs["band"] is None
    assert "Titel A" in gen.call_args.args[0]["post_text"]
    assert gen.call_args.args[1] == "POV"
    assert kwargs["persona_voice_de"] == swot.ACCOUNT_VOICES["LinkedIn Robert"]
    assert out == {"text": "TEXT", "soundbyte": "SB", "kontext": "CEO",
                   "skeleton": "TYP: Waage"}
