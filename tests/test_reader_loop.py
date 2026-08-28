"""Leser-Loop (Spec 2026-08-28): Leser, bis zu zwei chirurgische Reparaturen,
Verwerfen bei Restbefund. Modell gemockt, Teile-Call herausgefiltert."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps

POST = {"influencer": "Test", "post_text": "Thema: Forecast\nKurzbeschreibung: Annahmen",
        "likes": 0, "comments": 0, "shares": 0}
BAD = "Den Forecast baut man auf und denkt, die Zahlen stimmen. Stimmen sie nicht.\n\nDas Problem sitzt in den Annahmen."
GOOD = "Den Forecast baut man auf und denkt, die Zahlen stimmen. Tun sie nicht.\n\nDas Problem sitzt in den Annahmen."
FIND = '{"befunde": [{"art": "schriftdeutsch", "zitat": "Stimmen sie nicht.", "grund": "Verb vorn", "vorschlag": "Tun sie nicht."}]}'
CLEAN = '{"befunde": []}'


def _run(bodies):
    """bodies: Modellantworten in Aufrufreihenfolge (ohne Teile-Call).
    Gibt (de_draft, gesendete Prompts) zurueck."""
    captured, bodies = [], list(bodies)

    def fake_create(**kw):
        content = kw["messages"][0]["content"]
        resp = MagicMock()
        if content.startswith("Aus dem folgenden fertigen LinkedIn-Beitrag"):
            resp.content = [MagicMock(text="===SOUNDBYTE===\nx")]
            return resp
        captured.append(content)
        resp.content = [MagicMock(text=bodies.pop(0))]
        return resp

    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False, "en_draft": False,
                                       "naturalness_check": True}):
        c.messages.create.side_effect = fake_create
        de, *_ = ps.generate_post_and_image_prompt(POST, "Opinion")
    return de, captured


def test_clean_text_needs_generation_and_one_read_only():
    de, sent = _run(["===POST===\n" + GOOD, CLEAN])
    assert de.startswith(GOOD)   # startswith: blanket_cta haengt je Mandant einen CTA an
    assert len(sent) == 2
    assert "Du liest einen deutschen LinkedIn-Beitrag" in sent[1]
    assert "Thema: Forecast" in sent[1]


def test_one_finding_is_fixed_surgically_then_accepted():
    de, sent = _run(["===POST===\n" + BAD, FIND, GOOD, CLEAN])
    assert de.startswith(GOOD)
    assert len(sent) == 4
    assert sent[2].startswith("Du korrigierst einen deutschen LinkedIn-Beitrag chirurgisch")
    assert '[schriftdeutsch] "Stimmen sie nicht.": Verb vorn Vorschlag: Tun sie nicht.' in sent[2]
    assert BAD in sent[2]


def test_fix_rejected_by_length_guard_discards_text():
    de, sent = _run(["===POST===\n" + BAD, FIND, "Zu kurz."])
    assert de == ""
    assert len(sent) == 3


def test_residue_after_two_rounds_discards_text():
    de, sent = _run(["===POST===\n" + BAD, FIND, BAD, FIND, BAD, FIND])
    assert de == ""
    assert len(sent) == 6


def test_unreadable_reader_answer_keeps_text():
    de, sent = _run(["===POST===\n" + GOOD, "kein json"])
    assert de.startswith(GOOD)


def test_deterministic_finding_triggers_fix_without_llm_finding():
    tic = "Das ist kein Planungsproblem. Das ist ein Strukturproblem.\n\nDer Rest ist sauber."
    fixed = "Das Planungsverfahren ist nicht das Problem, die Struktur ist es.\n\nDer Rest ist sauber."
    de, sent = _run(["===POST===\n" + tic, CLEAN, fixed, CLEAN])
    assert de.startswith(fixed)
    assert "[schablone]" in sent[2]


def test_fix_output_failing_textwache_is_rejected():
    caps = "DAS IST DIE ANTWORT DARAUF.\n\nDen Forecast baut man auf und denkt, die Zahlen stimmen. Tun sie nicht."
    de, sent = _run(["===POST===\n" + BAD, FIND, caps])
    assert de == ""


SOFT = '{"befunde": [{"art": "schablone", "zitat": "Tun sie nicht.", "grund": "Pointe", "vorschlag": "x"}]}'


def test_soft_residue_after_two_rounds_keeps_text():
    # Trockenlauf 28.08.2026: Reparierer ersetzt Formel durch Formel; weiche
    # Reste verwerfen keinen Text mehr, nur harte (HARD_ARTEN) und Textwache.
    de, sent = _run(["===POST===\n" + GOOD, SOFT, GOOD, SOFT, GOOD, SOFT])
    assert de.startswith(GOOD)
    assert len(sent) == 6
