"""Prompt-Diaet SWOT (Spec 2026-08-28): keine Wortlaut-Verbote, keine
Selbstwidersprueche im Schreib-Prompt. Laedt die Config direkt, unabhaengig
vom Prozess-Mandanten der Test-Session."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

cfg = importlib.import_module("clients.swot.config")


def test_bans_carry_no_observer_permission_and_no_glaube_line():
    bans = cfg.TOKENS["LANGUAGE_BANS_DE"]
    assert "Erlaubt ist die Beobachterposition" not in bans
    assert "sehe ich" not in bans
    assert "Glaube" not in bans
    assert "kein Interim-CFO" in bans


def test_focus_topics_avoid_the_banned_kunstwort():
    assert "Uebergabefaehigkeit" not in cfg.TOKENS["FOCUS_TOPICS_DE"]
    assert "uebernehmen" in cfg.TOKENS["FOCUS_TOPICS_DE"]


def test_voice_head_demands_written_syntax_without_filler_wordlist():
    head = cfg.load_voice_profile("werner").split("\n")[2]
    assert "Schriftdeutsch" in head and "Verb an zweiter Stelle" in head
    assert "keine Echo-Antworten" in head
    assert "(halt, irgendwie" not in head


def test_voice_profiles_carry_no_spelled_out_formulas():
    for name in ("werner", "kulle"):
        p = cfg.load_voice_profile(name)
        assert "Das ist kein Tool-Problem" not in p
        assert "Das ist kein X-Problem" not in p
        assert "Game Changer" not in p and "Game-Changer" not in p
        assert "Kennst du das?" not in p
        assert "Was er nie sagen würde" in p


def test_cta_de_is_the_binding_wording():
    assert cfg.CTA_DE == ("30 Minuten mit unseren Planungs- und Konsolidierungsexperten, "
                          "kostenfrei: https://www.swot.de/demo-buchen/")
