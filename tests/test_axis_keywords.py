"""Achsen-Keywords bei jolly: acht Achsen, Umkehrabbildung eindeutig,
JOLLY_KEYWORDS ist abgeleitet. Kein Netz.

Liest jollys Config direkt statt ueber load_client: der Cache wuerde sonst auf
jolly festgenagelt und tests/test_axis_scrape.py liest danach jollys Achsen
statt SWOTs (gemessen 22.09.2026)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.jolly import config as jolly_config

import run_keyword_scrape as rks

ACHSEN = {
    "outbound_maschine", "daten_und_revops", "positionierung_und_angebot",
    "sales_prozess", "team_und_enablement", "inbound_und_content",
    "bestand_und_expansion", "ki_im_gtm",
}


def test_jolly_hat_alle_acht_achsen():
    by_axis = jolly_config.KEYWORDS_BY_AXIS
    assert set(by_axis) == ACHSEN


def test_jede_achse_mindestens_sechs_begriffe():
    by_axis = jolly_config.KEYWORDS_BY_AXIS
    duenn = {a: len(k) for a, k in by_axis.items() if len(k) < 6}
    assert not duenn, f"zu duenn besetzt: {duenn}"


def test_kein_begriff_in_zwei_achsen():
    by_axis = jolly_config.KEYWORDS_BY_AXIS
    alle = [k for keywords in by_axis.values() for k in keywords]
    assert len(alle) == len(set(alle))


def test_jolly_keywords_ist_abgeleitet():
    by_axis = jolly_config.KEYWORDS_BY_AXIS
    erwartet = {k for keywords in by_axis.values() for k in keywords}
    assert set(rks.JOLLY_KEYWORDS) == erwartet


def test_gelockte_begriffe_sind_alle_noch_drin():
    """Die 18 am 08.06.2026 gelockten Begriffe werden zugeordnet, nie ersetzt."""
    gelockt = {
        "revenue operations", "b2b lead generation", "go-to-market strategy",
        "cold email", "fractional cmo", "cold email deliverability",
        "email warmup", "buying committee", "ideal customer profile",
        "sales forecasting", "account based marketing", "intent data",
        "demand generation", "gtm engineering", "ai sdr",
        "ai personalization sales", "revops automation",
        "answer engine optimization",
    }
    assert gelockt <= set(rks.JOLLY_KEYWORDS)


def test_axis_for_keyword_trifft_die_achse():
    assert rks.axis_for_keyword("cold email") == "outbound_maschine"
    assert rks.axis_for_keyword("revenue operations") == "daten_und_revops"
    assert rks.axis_for_keyword("COLD EMAIL") == "outbound_maschine"
    assert rks.axis_for_keyword("voellig unbekannt") is None
