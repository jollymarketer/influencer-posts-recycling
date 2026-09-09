"""Textwache: Ueberlaenge wird gekuerzt, nicht verworfen (Richard 09.09.2026).

Anlass: im Sie-Umstellungslauf vom 08.09.2026 blieben drei Zeilen leer, weil
der Entwurf 5 bis 9 Prozent ueber dem Laengenband lag. Ein Neulauf schreibt
neu und landet wieder daneben, Streichen haelt den gepruefte Inhalt.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer as ps

LANG = "Der Vorlauf fehlt im Kalender. " * 40      # 1200 Zeichen
KURZ = "Der Vorlauf fehlt im Kalender. " * 30      # 900 Zeichen


def _antworten(texte):
    """Modell gibt der Reihe nach diese Texte zurueck; sammelt die Prompts."""
    prompts, rest = [], list(texte)

    def fake_create(**kw):
        prompts.append(kw["messages"][0]["content"])
        resp = MagicMock()
        resp.content = [MagicMock(text=rest.pop(0))]
        return resp

    return fake_create, prompts


def test_finish_draft_shortens_instead_of_discarding():
    fake, prompts = _antworten([KURZ])
    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False}):
        c.messages.create.side_effect = fake
        out = ps._finish_draft(LANG, 1000)
    assert out == KURZ.strip()
    assert len(prompts) == 1
    assert "Kuerze den folgenden LinkedIn-Beitrag auf hoechstens 1000 Zeichen" in prompts[0]


def test_within_tolerance_is_kept_instead_of_discarded():
    # Ziel bleibt 1000, verworfen wird erst ueber 1100 (Richard 09.09.2026).
    knapp = "Der Vorlauf fehlt im Kalender. " * 34      # 1054 Zeichen
    fake, prompts = _antworten([knapp, knapp])
    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False}):
        c.messages.create.side_effect = fake
        out = ps._finish_draft(LANG, 1000)
    assert 1000 < len(out) <= ps.accept_cap(1000)
    assert len(prompts) == ps._SHORTEN_TRIES      # das Ziel bleibt 1000


def test_finish_draft_tries_twice_then_discards():
    # Beide Versuche bleiben ueber der Toleranzgrenze: die Zeile bleibt leer.
    fast = "Der Vorlauf fehlt im Kalender. " * 38
    immer_noch = "Der Vorlauf fehlt im Kalender. " * 37
    fake, prompts = _antworten([fast, immer_noch])
    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False}):
        c.messages.create.side_effect = fake
        out = ps._finish_draft(LANG, 1000)
    assert out == ""
    assert len(prompts) == ps._SHORTEN_TRIES


def test_caps_violation_is_not_shortened():
    # Grossbuchstaben-Block bleibt ein Verwerfungsgrund ohne Modell-Call.
    text = "SO GEHT DAS NICHT.\n\nDer Vorlauf fehlt im Kalender."
    with patch("tools.post_scorer.client") as c, \
         patch.dict(ps._cfg.FEATURES, {"grammar_check": False}):
        out = ps._finish_draft(text, 1000)
    assert out == ""
    assert c.messages.create.call_count == 0
