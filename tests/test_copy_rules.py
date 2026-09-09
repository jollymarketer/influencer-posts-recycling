"""Kundenregeln (tools/copy_rules): reine Funktionen, kein Modell.

Anlass: Notion-Kommentare von Inga Baumert und Muhammed Doganguezel (SWOT,
01. bis 07.09.2026) an neun Beitraegen; Richard hat sieben davon am
08.09.2026 als Regeln freigegeben. Jede Regel ist hier mit dem Fundtext aus
dem Redaktionsplan belegt.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import copy_rules as cr

RULES = {
    "role_frames": {
        "Robert Werner": {
            "erlaubt": "Demo, Workshop, Erstgespräch",
            "verboten": [r"Einf(?:ü|ue)hrungsprojekt\w*", r"Daten(?:ü|ue)bernahme\w*"],
        },
        "Christian Kulle": {
            "erlaubt": "Datenübernahme, Kundenprojekt",
            "verboten": [r"Erstgespr(?:ä|ae)ch\w*", r"\bDemo\b"],
        },
    },
    "disparagement": [r"falsch (?:gebaut|umgesetzt)", r"aber schlechter", r"niemand wusste"],
    "term_map": {"Cashforecast": "Liquiditätsplanung", "Liquiditätsprognose": "Liquiditätsplanung"},
    "address": "Sie",
    "cta_bridge": True,
    "structure_max_repeat": 2,
}
# Anrede-Mechanik in die andere Richtung (Richard 08.09.2026: SWOT siezt; die
# du-Variante bleibt geprueft, weil andere Mandanten sie fahren koennen).
DU_RULES = {**RULES, "address": "du"}
ROBERT = "Du schreibst als Robert Werner, Leiter Vertrieb und Akademie."
CHRISTIAN = "Du schreibst als Christian Kulle von der SWOT Controlling GmbH."


def _arten(findings):
    return [f["art"] for f in findings]


# --- Rollen-Wahrheit ---------------------------------------------------------

def test_role_frame_flags_forbidden_situation_for_the_named_speaker():
    # Fundtext Werner 22.09.2026 (Inga: "Robert selbst fuehrt keine
    # Einfuehrungsprojekte").
    text = ("Beim Einführungsprojekt letzte Woche hat mich der Controller "
            "unterbrochen.\n\nIhnen fehlt das Mapping.")
    out = cr.findings(text, ROBERT, RULES)
    rolle = [f for f in out if f["art"] == "rolle"]
    assert len(rolle) == 1
    assert rolle[0]["zitat"] == "Einführungsprojekt"
    assert "Demo, Workshop, Erstgespräch" in rolle[0]["vorschlag"]
    # Fuer Christian ist dieselbe Situation richtig.
    assert "rolle" not in _arten(cr.findings(text, CHRISTIAN, RULES))


def test_role_frame_ignores_unknown_speaker_and_missing_rules():
    text = "Beim Einführungsprojekt letzte Woche.\n\nSie kennen das."
    assert cr.findings(text, "Du schreibst fuer die Unternehmensseite.", RULES) == []
    assert cr.findings(text, ROBERT, None) == []
    assert cr.findings(text, ROBERT, {}) == []


# --- Keine Abwertung ---------------------------------------------------------

def test_disparagement_pattern_is_a_finding_with_neutral_suggestion():
    # Fundtext Werner 16.09.2026, Inga: "impliziert, dass das Verfahren
    # zuvor schlicht falsch umgesetzt wurde".
    text = ("Hans-Joachim Möbes hat seinen Monatsabschluss auf einen Tag "
            "gebracht. Nicht durch Fleiß, sondern weil das Verfahren vorher "
            "falsch gebaut war.\n\nPrüfen Sie, wie viele Ihrer Vorlagen deckungsgleich sind.")
    out = [f for f in cr.findings(text, ROBERT, RULES) if f["art"] == "abwertung"]
    assert len(out) == 1
    assert out[0]["zitat"] == "falsch gebaut"
    assert "neutral" in out[0]["vorschlag"]


def test_disparagement_without_a_subject_stays_soft():
    # Richard 09.09.2026: ein Missstand ohne Adressaten ist der Painpoint des
    # Beitrags. Fundtext aus dem Nachfuell-Lauf 08.09.2026.
    text = ("Zwischen den Systemen lag eine Tabelle, niemand wusste, wer sie "
            "pflegt.\n\nPrüfen Sie, wo Ihre Zuordnung liegt.")
    out = [f for f in cr.findings(text, ROBERT, RULES)
           if f["art"].startswith("abwertung")]
    assert [f["art"] for f in out] == ["abwertung_anonym"]
    assert "niemandem zuschreibt" in out[0]["grund"]


def test_same_wording_with_a_named_subject_stays_hard():
    text = ("Hans-Joachim Möbes hatte das Verfahren falsch gebaut.\n\n"
            "Prüfen Sie, wo Ihre Zuordnung liegt.")
    out = [f for f in cr.findings(text, ROBERT, RULES)
           if f["art"].startswith("abwertung")]
    assert [f["art"] for f in out] == ["abwertung"]


def test_a_role_in_the_sentence_is_a_subject_too():
    text = ("Der Controller hatte das Mapping falsch gebaut.\n\n"
            "Prüfen Sie, wo Ihre Zuordnung liegt.")
    out = [f for f in cr.findings(text, ROBERT, RULES)
           if f["art"].startswith("abwertung")]
    assert [f["art"] for f in out] == ["abwertung"]


# --- Fachbegriff aus dem VoC-Korpus ------------------------------------------

def test_term_map_quotes_the_whole_compound_and_proposes_replacement():
    # Fundtext Werner 23.09.2026 (Inga: "waere Liquiditaetsprognose das
    # passendere Wort?"). VoC-Korpus: Liquiditaetsplanung 36, Prognose 1,
    # Cashforecast 0.
    text = ("Beim ersten 13-Wochen-Cashforecast stimmen die Zahlen fast nie.\n\n"
            "Prüfen Sie Ihre Annahmen, bevor Sie die Zahlen weitergeben.")
    out = [f for f in cr.findings(text, ROBERT, RULES) if f["art"] == "fachbegriff"]
    assert len(out) == 1
    assert out[0]["zitat"] == "13-Wochen-Cashforecast"
    assert out[0]["vorschlag"] == "13-Wochen-Liquiditätsplanung"


def test_term_map_reports_each_term_once():
    text = "Cashforecast hier, Cashforecasts dort.\n\nSie sehen es."
    out = [f for f in cr.findings(text, ROBERT, RULES) if f["art"] == "fachbegriff"]
    assert len(out) == 1


# --- Ein Register: Sie ---------------------------------------------------------

def test_du_form_is_a_register_finding():
    # Richard 08.09.2026: SWOT-Content wird gesiezt, der Bestand stand in du/ihr.
    text = ("Der Vorlauf fehlt im Kalender.\n\nPrüfen Sie das, bevor euch der "
            "Stichtag einholt.")
    out = [f for f in cr.findings(text, CHRISTIAN, RULES) if f["art"] == "register"]
    assert len(out) == 1
    assert "euch" in out[0]["zitat"]
    assert "Sie-Form" in out[0]["vorschlag"]


def test_ihr_as_pronoun_is_a_finding_but_possessive_ihr_is_not():
    pronomen = ("Die Frist steht.\n\nWenn ihr das jetzt aufsetzt, reicht die Zeit.")
    assert "register" in _arten(cr.findings(pronomen, ROBERT, RULES))
    besitz = ("Kunden bereiten ihr Zahlenwerk für die Bank auf.\n\nIhre Annahmen "
              "sollten Sie dabei dokumentieren.")
    assert "register" not in _arten(cr.findings(besitz, ROBERT, RULES))


def test_sie_form_mid_sentence_is_a_register_finding_when_the_client_says_du():
    # Ingas CTA-Vorschlag vom 07.09.2026 in Sie-Form unter einem ihr-Text.
    text = ("Der Vorlauf fehlt im Kalender.\n\nIhr wollt noch in diesem Jahr "
            "starten? Lassen Sie uns besprechen, welche Schritte jetzt nötig sind.")
    out = [f for f in cr.findings(text, CHRISTIAN, DU_RULES) if f["art"] == "register"]
    assert len(out) == 1
    assert "Lassen Sie uns" in out[0]["zitat"]


def test_plural_sie_at_sentence_start_is_not_a_register_finding():
    text = ("Die Zahlen sahen schlüssig aus. Sie stimmten trotzdem nicht, weil "
            "die Annahmen fehlten.\n\nPrüft, wer welche Annahme gesetzt hat.")
    assert "register" not in _arten(cr.findings(text, ROBERT, DU_RULES))


# --- Ein CTA mit Bruecke -------------------------------------------------------

def test_closing_question_is_a_cta_finding():
    # Fundtext Werner 15.09.2026: Schlussfrage plus Terminzeile darunter.
    text = ("Ein übergabefähiges Modell braucht vier Dinge.\n\n"
            "Wie lange würde es bei Ihnen dauern?")
    out = [f for f in cr.findings(text, ROBERT, RULES) if f["art"] == "cta"]
    assert len(out) == 1
    assert out[0]["zitat"] == "Wie lange würde es bei Ihnen dauern?"


def test_last_paragraph_without_reader_address_is_a_cta_finding():
    # Fundtext Kulle 17.09.2026, Inga: "der Link kommt komplett ohne
    # einleitende Worte".
    text = ("Vier Fristen bis Anfang 2027.\n\n"
            "Der Vorlauf trägt keinen Kalendertermin. Den trägt kaum jemand ein.")
    out = [f for f in cr.findings(text, CHRISTIAN, RULES) if f["art"] == "cta"]
    assert len(out) == 1
    assert "Brücke" in out[0]["grund"]


def test_self_written_link_hint_is_a_cta_finding():
    text = ("Vier Fristen bis Anfang 2027.\n\n"
            "Wenn Sie das durchgehen wollen: den Link finden Sie im ersten Kommentar.")
    out = [f for f in cr.findings(text, CHRISTIAN, RULES) if f["art"] == "cta"]
    assert len(out) == 1
    assert "Kommentar" in out[0]["zitat"]


def test_bridge_paragraph_in_sie_form_passes():
    text = ("Vier Fristen bis Anfang 2027.\n\n"
            "Wenn Sie für Q1 2027 planen, lohnt es sich, den Vorlauf einmal "
            "gemeinsam durchzugehen.")
    assert "cta" not in _arten(cr.findings(text, CHRISTIAN, RULES))


# --- Strukturmuster hoechstens zweimal ---------------------------------------

def test_repeated_label_pattern_beyond_cap_is_a_struktur_finding():
    # Fundtext Kulle 15.09.2026: vier Annahme/Praxis-Paare (Muhammed:
    # "wieder zu KI-technisch").
    text = ("Viele denken, die Zahlen müssen stimmen.\n\n"
            "Annahme: Eine plausible Zahl genügt.\nPraxis: Ohne Quelle ist sie eine Behauptung.\n\n"
            "Annahme: Die Prognose gilt als Planungsinstrument.\nPraxis: Wer sie nach außen trägt, haftet.\n\n"
            "Annahme: Abweichungen erklärt man mündlich.\nPraxis: Wer nachreicht, hat verloren.\n\n"
            "Annahme: Das braucht nur die Eigenverwaltung.\nPraxis: Jeder Prüfer fragt danach.\n\n"
            "Haben Sie das hinterlegt, oder lebt das noch in Köpfen.")
    out = [f for f in cr.findings(text, CHRISTIAN, RULES) if f["art"] == "struktur"]
    assert len(out) == 1
    assert out[0]["zitat"].startswith("Annahme: Abweichungen")
    assert "4" in out[0]["grund"] and "2" in out[0]["grund"]


def test_two_pairs_and_numbered_lists_pass():
    text = ("Annahme: A.\nPraxis: B.\n\nAnnahme: C.\nPraxis: D.\n\n"
            "➊ Kontenrahmen ziehen\n➋ Zuordnen\n➌ Klären\n➍ Dokumentieren\n\n"
            "Prüfen Sie, ob Ihre Zuordnung als Regel dokumentiert ist.")
    assert "struktur" not in _arten(cr.findings(text, CHRISTIAN, RULES))


# --- Form der Befunde ----------------------------------------------------------

def test_findings_carry_the_reader_shape():
    text = "Beim Einführungsprojekt.\n\nWie lange dauert das bei Ihnen?"
    for f in cr.findings(text, ROBERT, RULES):
        assert set(f) == {"art", "zitat", "grund", "vorschlag"}
        assert f["zitat"] and f["zitat"] in text
