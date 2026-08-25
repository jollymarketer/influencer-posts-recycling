"""Natuerlichkeits-Stufe: reine Funktionen, kein Modellaufruf."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import naturalness as nat

NEGATIV = """Jede Einheit braucht ihr eigenes Planungsverfahren. Das höre ich oft.

Das ist kein Planungsproblem. Das ist ein Strukturproblem.

📍 Glaube: Jedes Mandat braucht eigene Strukturen.
Realität: Eine Standardvorlage reicht.

Nicht weil die Zahl falsch ist, sondern weil niemand sie erklären kann.

Ein Forecast, der nur in einer Hand funktioniert, ist kein Planungsinstrument. Er ist ein Risiko.

Wer die Vorlage erst nach dem dritten Mandat standardisiert, bezahlt sie als Reputationsschaden.

Wie viele Definitionen hat eure Personalquote gerade?"""


def test_tic_hits_finds_the_formulas_of_the_negative_example():
    names = [h.split(":")[0] for h in nat.tic_hits(NEGATIV)]
    assert "kein X-Problem, sondern Y-Problem" in names
    assert "Glaube als Fachwort" in names
    assert "Nicht weil ..., sondern weil" not in names   # Kulles echte Konstruktion, kein Tic
    assert "X ist kein Y. Es ist ein Z." in names
    assert "Wer X, hat/bezahlt Y (Sentenz)" in names


def test_tic_hits_flags_spoken_fillers():
    names = [h.split(":")[0] for h in nat.tic_hits("Also, das weiß halt keiner mehr.")]
    assert names == ["Fuellwort der gesprochenen Sprache"]
    assert nat.tic_hits("Alsosolche Halterung ist keine Sprache.") == []


def test_tic_hits_clean_text():
    text = ("Die zweite Gesellschaft kostet so viel Einrichtung wie die erste, "
            "weil der Kontenrahmen jedes Mal neu verhandelt wird. Das lässt sich "
            "vermeiden, wenn die Vorlage vor der zweiten Einheit steht.")
    assert nat.tic_hits(text) == []


def test_phrases_collects_observer_formula_and_closing_question():
    text = ("In Einführungsprojekten sehe ich das immer wieder: Zahlen ohne Quelle.\n\n"
            "Die eigentliche Frage ist eine andere.\n\nWie lange dauert das bei euch?")
    p = nat.phrases(text)
    assert "In Einführungsprojekten sehe ich" in p
    assert "Die eigentliche Frage" in p
    assert p[-1] == nat.CLOSING_QUESTION


def test_phrases_without_question_has_no_marker():
    assert nat.CLOSING_QUESTION not in nat.phrases("Ein Satz. Noch einer.")


def test_long_sentences_splits_on_newlines():
    long = " ".join(["Wort"] * 30) + "."
    text = "Kurz.\n" + long + "\n- Listenzeile mit fünf Wörtern"
    out = nat.long_sentences(text)
    assert len(out) == 1 and out[0].startswith("Wort Wort")


def test_avoid_note_lists_phrases_and_blocks_third_question():
    note = nat.avoid_note(["In Projekten sehe ich", nat.CLOSING_QUESTION, nat.CLOSING_QUESTION])
    assert "SCHON VERBRAUCHT" in note and "In Projekten sehe ich" in note
    assert "endet NICHT mit einer Frage" in note
    assert nat.avoid_note([]) == ""
    assert "endet NICHT" not in nat.avoid_note([nat.CLOSING_QUESTION])


def test_critic_prompt_with_and_without_voice():
    plain = nat.critic_prompt("Text A")
    assert "MASSSTAB" not in plain and "11." not in plain and "Text A" in plain
    voiced = nat.critic_prompt("Text A", "So redet Robert: kurz, mit Beispielen.")
    assert "MASSSTAB" in voiced and "So redet Robert" in voiced
    assert "11. Klingt der Text nach dieser Person" in voiced


def test_parse_verdict_tolerates_prose_and_garbage():
    v = nat.parse_verdict('Hier: {"note": 5, "fundstellen": ["a: b", "c: d"]} danke')
    assert v == {"note": 5, "fundstellen": ["a: b", "c: d"]}
    assert nat.parse_verdict("kein json") is None
    assert nat.parse_verdict('{"note": "x"}') is None
    assert nat.parse_verdict('{"note": 14}')["note"] == 10


def test_rewrite_note_carries_findings():
    note = nat.rewrite_note({"note": 4, "fundstellen": ["Glaube: sagt niemand"]},
                            ["Glaube als Fachwort: \"Glaube:\""], ["ein langer Satz"])
    assert "Note 4 von 10" in note and "Glaube: sagt niemand" in note
    assert "Formeln" in note and "aufteilen" in note
