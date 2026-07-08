"""Unit tests fuer sanitize_generated_text/_append_cta (Kundenfeedback lisocon 2026-07-08).
Pure functions, keine API-Calls."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.post_scorer import _append_cta, sanitize_generated_text


def test_strips_markdown_bold():
    raw = "**Terminology is not a translation problem.** It is an architecture problem."
    assert sanitize_generated_text(raw) == (
        "Terminology is not a translation problem. It is an architecture problem."
    )


def test_em_dash_becomes_comma():
    assert sanitize_generated_text("Das Layout — nicht der Text — kostet.") == (
        "Das Layout, nicht der Text, kostet."
    )


def test_unspaced_em_dash_becomes_comma():
    assert sanitize_generated_text("Layout—nicht Text") == "Layout, nicht Text"


def test_numeric_range_keeps_hyphen():
    assert sanitize_generated_text("10–20 Sprachen") == "10-20 Sprachen"


def test_dash_bullet_becomes_hyphen_bullet():
    assert sanitize_generated_text("– erster Punkt\n– zweiter Punkt") == (
        "- erster Punkt\n- zweiter Punkt"
    )


def test_ascii_box_untouched():
    box = "┌─────┐\n│ Merksatz │\n└─────┘"
    assert sanitize_generated_text(box) == box


def test_append_cta_adds_line_at_bottom():
    post = "Body.\n\n#Localization #InDesign\n"
    assert _append_cta(post, "Sounds interesting? Visit us at www.in2go.io") == (
        "Body.\n\n#Localization #InDesign\n\nSounds interesting? Visit us at www.in2go.io"
    )


def test_append_cta_empty_cta_is_noop():
    assert _append_cta("Body.", "") == "Body."


def test_lisocon_config_has_logo_and_cta():
    from clients.lisocon import config as lisocon

    assert lisocon.CTA_DE == "Interessant? Besuchen Sie uns auf www.in2go.io"
    assert "www.in2go.io" in lisocon.CTA_EN
    logo = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "Resources", lisocon.LOGO_FILE)
    assert os.path.isfile(logo)
