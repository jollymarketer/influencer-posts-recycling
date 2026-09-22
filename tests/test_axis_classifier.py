"""Klassifizierer-Sperren: nur jolly, nur mit Flag. Kein Netz, kein Anthropic-Call.

Baut die Config als SimpleNamespace statt ueber load_client: der Cache wuerde
sonst auf jolly festgenagelt und tests/test_axis_scrape.py liest danach jollys
Achsen statt SWOTs (gemessen 22.09.2026)."""
import os
import sys
import types

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import axis_classifier


def _cfg(name, flags):
    return types.SimpleNamespace(NAME=name, FEATURES=flags)


def test_noop_ohne_flag(monkeypatch):
    def nie(*a, **k):
        raise AssertionError("classify_post darf ohne Flag nicht laufen")
    monkeypatch.setattr(axis_classifier, "classify_post", nie)
    rows = [{"post_url": "https://x/1", "post_text": "irgendwas"}]
    assert axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {})) == {}


def test_harter_abbruch_bei_fremdem_mandanten():
    rows = [{"post_url": "https://x/1", "post_text": "irgendwas"}]
    with pytest.raises(SystemExit) as exc:
        axis_classifier.classify_rows(rows, cfg=_cfg("swot", {"axis_classifier": True}))
    assert "jolly" in str(exc.value)


def test_abbruch_auch_ohne_flag_bei_fremdem_mandanten():
    """Reihenfolge der Sperren: Mandant zuerst. Ein fremder Mandant darf nicht
    still als No-Op durchlaufen, sonst faellt der Fehler nie auf."""
    rows = [{"post_url": "https://x/1", "post_text": "irgendwas"}]
    with pytest.raises(SystemExit):
        axis_classifier.classify_rows(rows, cfg=_cfg("lisocon", {}))


def test_klassifiziert_und_schreibt_zurueck(monkeypatch):
    monkeypatch.setattr(axis_classifier, "classify_post", lambda text: "ki_im_gtm")
    geschrieben = []
    monkeypatch.setattr(axis_classifier, "set_axis",
                        lambda url, axis: geschrieben.append((url, axis)))
    rows = [{"post_url": "https://x/1", "post_text": "AI SDR Agenten"}]
    ergebnis = axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {"axis_classifier": True}))
    assert ergebnis == {"ki_im_gtm": 1}
    assert geschrieben == [("https://x/1", "ki_im_gtm")]


def _antwort(text):
    """Stellt die Antwortform der Messages-API nach: resp.content[0].text."""
    return types.SimpleNamespace(content=[types.SimpleNamespace(text=text)])


def test_unbekannte_antwort_wird_null(monkeypatch):
    """Eine erfundene Achse ist teurer als keine: der Deckel wuerde danach am
    falschen Wert sperren. Geprueft an classify_post, nicht an classify_rows --
    dort liegt der Filter gegen AXES."""
    monkeypatch.setattr(axis_classifier, "client", types.SimpleNamespace(
        messages=types.SimpleNamespace(
            create=lambda **k: _antwort('{"axis": "erfundene_achse"}'))))
    assert axis_classifier.classify_post("x" * 200) is None


def test_kaputte_antwort_wird_null(monkeypatch):
    def krachen(**k):
        raise RuntimeError("429 rate limit")
    monkeypatch.setattr(axis_classifier, "client",
                        types.SimpleNamespace(messages=types.SimpleNamespace(create=krachen)))
    assert axis_classifier.classify_post("x" * 200) is None


def test_gueltige_antwort_kommt_durch(monkeypatch):
    monkeypatch.setattr(axis_classifier, "client", types.SimpleNamespace(
        messages=types.SimpleNamespace(
            create=lambda **k: _antwort('Hier: {"axis": "sales_prozess"} fertig'))))
    assert axis_classifier.classify_post("x" * 200) == "sales_prozess"


def test_null_antwort_wird_zurueckgeschrieben(monkeypatch):
    """'Passt in keine Achse' muss bis in set_axis durchlaufen, sonst holt der
    naechste Backfill denselben Grenzfall erneut."""
    monkeypatch.setattr(axis_classifier, "classify_post", lambda text: None)
    geschrieben = []
    monkeypatch.setattr(axis_classifier, "set_axis",
                        lambda url, axis: geschrieben.append((url, axis)))
    rows = [{"post_url": "https://x/9", "post_text": "Rezept fuer Brot"}]
    ergebnis = axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {"axis_classifier": True}))
    assert ergebnis == {"null": 1}
    assert geschrieben == [("https://x/9", None)]


def test_zeilen_ohne_url_werden_uebersprungen(monkeypatch):
    monkeypatch.setattr(axis_classifier, "classify_post", lambda text: "sales_prozess")
    monkeypatch.setattr(axis_classifier, "set_axis", lambda url, axis: None)
    rows = [{"post_text": "kein url"}, {"post_url": "https://x/2", "post_text": "t"}]
    ergebnis = axis_classifier.classify_rows(rows, cfg=_cfg("jolly", {"axis_classifier": True}))
    assert ergebnis == {"sales_prozess": 1}


def test_kurzer_text_kostet_keinen_call(monkeypatch):
    """Ersetzt den ganzen client, nicht dessen messages: LazyAnthropic baut den
    echten Client erst beim Attributzugriff, ein setattr darauf wuerde ihn
    aufwecken und einen Key verlangen."""
    def nie(*a, **k):
        raise AssertionError("kein Anthropic-Call fuer sieben Zeichen")
    monkeypatch.setattr(axis_classifier, "client",
                        types.SimpleNamespace(messages=types.SimpleNamespace(create=nie)))
    assert axis_classifier.classify_post("zu kurz") is None


def test_alle_acht_achsen_im_prompt():
    for achse in axis_classifier.AXES:
        assert achse in axis_classifier.PROMPT
    assert len(axis_classifier.AXES) == 8
