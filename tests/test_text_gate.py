"""Textwache: reine Funktionen, kein Modellaufruf."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import text_gate as tg


def test_caps_words_ignores_acronyms():
    text = "IFRS 18 und DATEV bleiben, aber DREI PRUEFSCHRITTE nicht."
    assert tg.caps_words(text) == ["DREI", "PRUEFSCHRITTE"]


def test_caps_lines_finds_block_but_not_acronym_line():
    text = ("Der Stichtag ist nicht das Problem.\n"
            "DREI PRÜFSCHRITTE VOR DEM BANKGESPRÄCH\n"
            "IFRS 18 mit EBITDA\n")
    assert tg.caps_lines(text) == ["DREI PRÜFSCHRITTE VOR DEM BANKGESPRÄCH"]


def test_umlaut_candidates_hits_transliterations():
    text = "Der Uebergabetest zeigt, ob die Verknuepfungen erklaert sind."
    assert tg.umlaut_candidates(text) == ["Uebergabetest", "Verknuepfungen", "erklaert"]


def test_umlaut_candidates_spares_real_words():
    text = ("Der Bauer hat neue Quellen, aktuell und manuell gepflegt, zuerst "
            "vom Influencer Michael aus Israel, dann per Due Diligence, Revue "
            "und Statue. Konsequenz: Steuerberater Manuel bleibt.")
    assert tg.umlaut_candidates(text) == []


def test_umlaut_candidates_dedupes_in_order():
    assert tg.umlaut_candidates("Pruefer und Pruefer und Aenderung") == ["Pruefer", "Aenderung"]


def test_hard_violations_caps_and_length():
    text = "EIN BLOCK IN GROSSBUCHSTABEN\n" + "x" * 1000
    out = tg.hard_violations(text, 900)
    assert len(out) == 2
    assert "Grossbuchstaben" in out[0]
    assert "erlaubt sind hoechstens 900" in out[1]


def test_violations_adds_umlaut_line_but_hard_stays_clean():
    text = "Die Uebergabe klappt."
    assert tg.hard_violations(text, 1800) == []
    assert tg.violations(text, 1800) == ["ae/oe/ue statt Umlaut: Uebergabe"]


def test_clean_text_has_no_violations():
    text = "Die Übergabe klappt, weil die Prämissen dokumentiert sind. GuV und IFRS 18 bleiben."
    assert tg.violations(text, 1800) == []
