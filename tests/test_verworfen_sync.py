"""Zuordnung verworfener Plan-Zeilen zu Themen-DB-Zeilen (reine Logik)."""
import os
import sys

os.environ.setdefault("CLIENT", "swot")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_verworfen_sync import match_verworfen


def _topic(pid, title="", title_de="", status="Hub needed"):
    return {"page_id": pid, "title": title, "title_de": title_de, "status": status}


def test_match_ueber_title_de_und_title():
    topics = [_topic("a", title="EN mining title", title_de="Deutscher Titel"),
              _topic("b", title="Nur englischer Titel")]
    matches, unmatched = match_verworfen(
        ["Deutscher Titel", "Nur englischer Titel"], topics)
    assert [t["page_id"] for t in matches] == ["a", "b"]
    assert unmatched == []


def test_umbetitelte_zeile_wird_gemeldet_nie_geraten():
    topics = [_topic("a", title_de="Original-Titel aus dem Mining")]
    matches, unmatched = match_verworfen(["Von Hand umbenannter Titel"], topics)
    assert matches == []
    assert unmatched == ["Von Hand umbenannter Titel"]


def test_200_zeichen_schnitt_matcht():
    # write_proposals schreibt titel[:200]; die Themen-DB traegt den vollen Titel.
    lang = "T" * 250
    topics = [_topic("a", title_de=lang)]
    matches, unmatched = match_verworfen([lang[:200]], topics)
    assert [t["page_id"] for t in matches] == ["a"]
    assert unmatched == []


def test_whitespace_und_case_normalisiert():
    topics = [_topic("a", title_de="Excel  am   Limit")]
    matches, _ = match_verworfen(["excel am limit"], topics)
    assert [t["page_id"] for t in matches] == ["a"]


def test_doppelte_plan_zeilen_treffen_thema_nur_einmal():
    topics = [_topic("a", title_de="Titel")]
    matches, _ = match_verworfen(["Titel", "Titel"], topics)
    assert len(matches) == 1
