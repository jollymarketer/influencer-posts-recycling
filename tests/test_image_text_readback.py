"""Text-Readback nach der Bildgenerierung (tools/kieai_image.py).

Der Soll-Text steht als Marker im Prompt; nach dem Render liest Claude Vision
den Bildtext, ein Mismatch loest einen neuen Render aus, nach dem letzten
Versuch bricht der Job ab (fail-closed, Status "Image Failed" beim Aufrufer).
Kein kie.ai-, kein Anthropic-Aufruf.
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import kieai_image as ki


# --- Marker-Parser -------------------------------------------------------------

def test_required_text_from_prompt_reads_every_marker():
    prompt = (
        "Create a card.\n"
        f'{ki.RENDER_TEXT_MARKER} "Planung ist kein Ritual"\n'
        "Composition: ...\n"
        f'{ki.RENDER_TEXT_MARKER} "73%"\n'
    )
    assert ki.required_text_from_prompt(prompt) == ["Planung ist kein Ritual", "73%"]


def test_required_text_from_prompt_empty_without_marker():
    assert ki.required_text_from_prompt("Create a premium cover, no text.") == []


def test_render_text_line_strips_inner_quotes():
    line = ki.render_text_line('Er sagte "nein" zur Planung')
    assert ki.required_text_from_prompt(line) == ["Er sagte nein zur Planung"]


# --- Vergleich -----------------------------------------------------------------

def test_text_matches_ignores_case_whitespace_and_punctuation():
    assert ki.text_matches("Planung ist kein Ritual",
                           "PLANUNG\nIST KEIN\nRITUAL.")


def test_text_matches_keeps_umlauts_strict():
    assert ki.text_matches("Liquidität zählt", "LIQUIDITÄT ZÄHLT")
    assert not ki.text_matches("Liquidität zählt", "LIQUIDITAT ZAHLT")


def test_text_matches_accepts_decomposed_unicode():
    # Vision liefert manchmal a + combining diaeresis statt des Umlaut-Zeichens.
    assert ki.text_matches("zählt", "zählt")


def test_text_matches_tolerates_hyphenated_line_break():
    assert ki.text_matches("Liquiditätsplanung", "Liquiditäts-\nplanung")


def test_text_matches_fails_on_missing_word():
    assert not ki.text_matches("Planung ist kein Ritual", "Planung ist Ritual")


# --- Retry-Schleife ------------------------------------------------------------

def test_generate_image_retries_with_note_after_text_mismatch():
    calls = []

    def fake_job(prompt, aspect_ratio, strip_marks=True, model=ki.DEFAULT_MODEL):
        calls.append(prompt)
        if len(calls) == 1:
            raise ki.TextMismatch("erwartet 'Ritual', gelesen 'Ritval'")
        return "https://img/ok.png"

    with patch.object(ki, "_run_kie_job", side_effect=fake_job), \
         patch.object(ki.time, "sleep"):
        url = ki.generate_image("Base prompt", aspect_ratio="1:1")

    assert url == "https://img/ok.png"
    assert len(calls) == 2
    assert calls[0] == "Base prompt"
    assert calls[1].startswith("Base prompt")
    assert ki.TEXT_RETRY_NOTE.strip() in calls[1]


def test_generate_image_gives_up_after_text_max_attempts():
    calls = []

    def fake_job(prompt, aspect_ratio, strip_marks=True, model=ki.DEFAULT_MODEL):
        calls.append(prompt)
        raise ki.TextMismatch("immer falsch")

    with patch.object(ki, "_run_kie_job", side_effect=fake_job), \
         patch.object(ki.time, "sleep"):
        try:
            ki.generate_image("Base prompt", aspect_ratio="1:1")
        except RuntimeError as e:
            assert "immer falsch" in str(e)
        else:
            raise AssertionError("kein Abbruch nach Text-Mismatch")

    assert len(calls) == ki.TEXT_MAX_ATTEMPTS


def test_verify_rendered_text_skips_without_expected_text():
    with patch.object(ki, "_read_image_text") as read:
        ki._verify_rendered_text(b"png", [])
    read.assert_not_called()


def test_verify_rendered_text_raises_text_mismatch():
    with patch.object(ki, "_read_image_text", return_value="PLANUNG IST RITVAL"):
        try:
            ki._verify_rendered_text(b"png", ["Planung ist kein Ritual"])
        except ki.TextMismatch as e:
            assert "Planung ist kein Ritual" in str(e)
            assert "PLANUNG IST RITVAL" in str(e)
        else:
            raise AssertionError("Mismatch nicht erkannt")


def test_verify_rendered_text_passes_on_match():
    with patch.object(ki, "_read_image_text", return_value="Planung\nist kein Ritual"):
        ki._verify_rendered_text(b"png", ["Planung ist kein Ritual"])
