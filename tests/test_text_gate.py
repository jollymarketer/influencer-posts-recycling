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


# Rhythmus und Strukturformeln (Repo-Vergleich linkedin-agent-skill,
# 14.09.2026): sprachneutrale Masse aus detect.py, deutsch nachgebaute
# Strukturmuster. Alles weich: nur der Neulauf-Hinweis, nie Verwerfen.

UNIFORM = ("Der Forecast steht im Excel. Die Zahlen kommen aus drei Quellen. "
           "Niemand kennt alle Annahmen. Das Bankgespräch ist am Freitag. "
           "Der Controller baut die Brücke.")
MIXED = ("Der Forecast steht im Excel. Die Zahlen kommen aus drei Quellen, "
         "die niemand im Haus vollständig kennt, weil jede Abteilung ihre "
         "eigene Ablage pflegt. Stimmt das? Am Freitag ist das Bankgespräch, "
         "und bis dahin muss die Brücke zwischen Planung und Ist stehen.")


def test_sentence_length_cv_none_below_four_sentences():
    assert tg.sentence_length_cv("Kurz. Noch kürzer. Ein dritter Satz.") is None


def test_sentence_length_cv_separates_uniform_from_mixed_rhythm():
    assert tg.sentence_length_cv(UNIFORM) < tg.MIN_SENTENCE_CV
    assert tg.sentence_length_cv(MIXED) > tg.MIN_SENTENCE_CV


def test_uniform_bullets_flags_equal_length_list_and_spares_varied():
    gleich = "Text.\n- Kontenrahmen vor der zweiten Einheit\n- Planung vor dem ersten Mandat\n- Abgrenzung vor dem ersten Abschluss"
    assert len(tg.uniform_bullets(gleich)) == 3
    variiert = "Text.\n- Kontenrahmen\n- Planung vor dem ersten Mandat, sonst rechnet jeder doppelt\n- Abgrenzung vor dem Abschluss"
    assert tg.uniform_bullets(variiert) == []
    assert tg.uniform_bullets("Text.\n- eins zwei\n- drei vier") == []   # unter drei Punkten


def test_shape_notes_catch_lowercase_triad_but_not_a_noun_list():
    assert any("Dreier" in n for n in tg.shape_notes("Das Modell ist schneller, besser und günstiger."))
    assert tg.shape_notes("Wir nutzen Excel, Word und PowerPoint.") == []


def test_shape_notes_catch_one_line_pointe_question():
    text = "Der Forecast stand nach drei Wochen.\n\nDas Ergebnis?\n\nNiemand las ihn."
    assert any("Pointen-Frage" in n for n in tg.shape_notes(text))
    assert tg.shape_notes("Das Ergebnis? Niemand las ihn.") == []   # nicht als eigene Zeile


def test_violations_carry_shape_notes_but_hard_violations_do_not():
    assert tg.hard_violations(UNIFORM, 1800) == []
    assert any("Satzlaengen" in p for p in tg.violations(UNIFORM, 1800))
    mit_pointe = MIXED + "\n\nDas Ergebnis?\n\nNiemand las den Forecast, weil er zu spät kam."
    assert tg.hard_violations(mit_pointe, 1800) == []
    assert any("Pointen-Frage" in p for p in tg.violations(mit_pointe, 1800))


def test_human_writing_samples_pass_the_rhythm_check():
    """Kalibrierung: Kulles Schreibproben (clients/swot/voices/kulle.md,
    aus Call-Transkripten) muessen ohne Rhythmus-Befund durchgehen."""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "clients", "swot", "voices", "kulle.md")
    with open(path, encoding="utf-8") as fh:
        md = fh.read()
    block = md.split("## Schreibmuster", 1)[1].split("## Datengrundlage", 1)[0]
    assert len(block) > 300
    assert not any("Satzlaengen" in n for n in tg.shape_notes(block))


def test_shape_notes_flag_a_first_line_over_140_chars():
    lang = "A" * 150 + "."
    text = "\n\n" + lang + "\n\nZweiter Absatz."
    assert any("Erste Zeile 151 Zeichen" in n for n in tg.shape_notes(text))
    assert not any("Erste Zeile" in n for n in tg.shape_notes("Kurz.\n\n" + lang))
