"""Mandantenspezifische Keyword-Liste und Scoring-Justierung.

Hintergrund (Richard, 19.08.2026): SWOT braucht eine eigene Keyword-Liste und ein
anderes Scoring als jolly. Die Keyword-Liste in run_keyword_scrape.py ist jollys
eigene (gelockt 08.06.2026) und darf nicht still fuer andere Mandanten gelten.
In der stillen DACH-Controlling-Nische spuelt volles Viralitaets-Gewicht
Vendor-Marketing nach oben, und der Score-Floor 25/60 reisst regelmaessig.
"""
import pytest

from run_keyword_scrape import resolve_keywords, JOLLY_KEYWORDS
from tools.post_scorer import weighted_total


class _Cfg:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


def test_client_keywords_win_over_default():
    cfg = _Cfg(KEYWORDS=["liquiditaetsplanung", "konsolidierung"])
    assert resolve_keywords(cfg, "swot") == ["liquiditaetsplanung", "konsolidierung"]


def test_jolly_falls_back_to_locked_default():
    assert resolve_keywords(_Cfg(), "jolly") == JOLLY_KEYWORDS


def test_foreign_client_without_keywords_fails_loud():
    with pytest.raises(SystemExit) as e:
        resolve_keywords(_Cfg(), "swot")
    assert "KEYWORDS" in str(e.value)


def test_empty_client_keywords_fail_loud():
    with pytest.raises(SystemExit):
        resolve_keywords(_Cfg(KEYWORDS=[]), "swot")


def test_virality_weight_default_is_unchanged():
    assert weighted_total(40, 9, 1.0) == 49


def test_virality_weight_dampens_engagement():
    # SWOT: 0.3 -> ein viraler Post gewinnt nicht mehr allein durch Reichweite
    assert weighted_total(40, 10, 0.3) == 43
    assert weighted_total(40, 0, 0.3) == 40


def test_quiet_niche_post_beats_loud_one_under_weighting():
    quiet = weighted_total(42, 1, 0.3)    # fachlich stark, kaum Reaktionen
    loud = weighted_total(36, 10, 0.3)    # duenn, aber viral
    assert quiet > loud
    # ungewichtet gewinnt der virale Post
    assert weighted_total(42, 1, 1.0) < weighted_total(36, 10, 1.0)


def test_swot_config_is_wired_for_research():
    from clients.swot import config as swot

    assert swot.FEATURES["keyword_scrape"] is True
    assert swot.FEATURES["topic_mining"] is True
    assert swot.FEATURES["supabase_persist"] is True
    assert len(swot.KEYWORDS) >= 10
    assert swot.VIRALITY_WEIGHT < 1.0
    assert swot.MIN_SCORE < 25


def test_swot_influencer_list_has_no_software_vendors():
    """Sperre Christian Kulle, 13.08.2026: keine Anbieter konkurrierender
    Planungs-, Konsolidierungs- oder Liquiditaetssoftware als Quelle."""
    import csv
    from pathlib import Path

    rows = list(csv.DictReader(
        (Path(__file__).resolve().parents[1] / "clients" / "swot" / "influencers.csv")
        .open(encoding="utf-8")))
    gesperrt = {"jedox", "corporate planning", "corporate planner", "lucanet",
                "agicap", "tidely", "idl", "prevero", "unit4", "cubus"}
    for row in rows:
        name = (row["Name"] or "").lower()
        assert not any(v in name for v in gesperrt), f"gesperrter Anbieter in der Liste: {row['Name']}"
