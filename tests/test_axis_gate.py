"""Achsen-Deckel und Pool-Rueckgriff. Reine Logik, kein Netz."""
import os
import sys

os.environ["CLIENT"] = "jolly"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.axis_gate import axis_of, blocked_axes, free_candidates, pool_candidates


def test_zwei_vorkommen_sperren():
    recent = ["daten_und_revops", "outbound_maschine", "daten_und_revops"]
    assert blocked_axes(recent) == {"daten_und_revops"}


def test_ein_vorkommen_sperrt_nicht():
    assert blocked_axes(["daten_und_revops", "outbound_maschine"]) == set()


def test_null_wird_nie_gesperrt():
    recent = ["null", "null", "null", "daten_und_revops"]
    assert blocked_axes(recent) == set()


def test_leeres_fenster_sperrt_nichts():
    assert blocked_axes([]) == set()


def test_kandidaten_ohne_achse_bleiben_drin():
    posts = [
        {"post_url": "a", "axis": "daten_und_revops"},
        {"post_url": "b", "axis": None},
        {"post_url": "c", "axis": "ki_im_gtm"},
    ]
    frei = free_candidates(posts, {"daten_und_revops"})
    assert [p["post_url"] for p in frei] == ["b", "c"]


def test_alles_gesperrt_gibt_leere_liste():
    posts = [{"post_url": "a", "axis": "ki_im_gtm"}]
    assert free_candidates(posts, {"ki_im_gtm"}) == []


def test_pool_zieht_nur_freie_achsen_und_ueberspringt_gesehene():
    rows = [
        {"post_url": "a", "axis": "daten_und_revops", "post_text": "x" * 300},
        {"post_url": "b", "axis": "ki_im_gtm", "post_text": "x" * 300},
        {"post_url": "c", "axis": "ki_im_gtm", "post_text": "x" * 300},
        {"post_url": "d", "axis": None, "post_text": "x" * 300},
    ]
    kandidaten = pool_candidates(rows, {"daten_und_revops"}, seen_urls={"c"})
    assert [r["post_url"] for r in kandidaten] == ["b", "d"]


def test_pool_verwirft_zu_kurze_texte():
    rows = [{"post_url": "a", "axis": "ki_im_gtm", "post_text": "kurz"}]
    assert pool_candidates(rows, set(), seen_urls=set()) == []


def test_axis_of_liest_beide_schreibweisen():
    assert axis_of({"axis": "ki_im_gtm"}) == "ki_im_gtm"
    assert axis_of({"source": "linkedin_search:sales_prozess"}) == "sales_prozess"
    assert axis_of({"source": "linkedin"}) is None
    assert axis_of({}) is None
