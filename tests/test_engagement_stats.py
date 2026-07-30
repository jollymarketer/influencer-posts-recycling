"""Tests fuer die Engagement-Auswertung. Reine Funktionen, kein Netz."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import engagement_stats as es


def _row(likes=None, comments=None, shares=None, **dims):
    return {"likes": likes, "comments": comments, "shares": shares, "dims": dims}


# --- engagement_score --------------------------------------------------------

def test_score_is_weighted():
    assert es.engagement_score(_row(10, 2, 1)) == 10 + 4 + 3


def test_unmeasured_row_is_none_not_zero():
    """Nie gemessen ist nicht dasselbe wie null Likes - sonst zieht jede
    frisch veroeffentlichte Zeile den Median nach unten."""
    assert es.engagement_score(_row()) is None
    assert es.engagement_score(_row(0, 0, 0)) == 0


def test_partial_measurement_counts():
    assert es.engagement_score(_row(likes=7)) == 7


def test_measured_rows_filters_and_annotates():
    rows = [_row(5, 0, 0), _row(), _row(1, 1, 0)]
    out = es.measured_rows(rows)
    assert [r["score"] for r in out] == [5, 3]


# --- aggregate ---------------------------------------------------------------

def test_aggregate_groups_by_dimension_value():
    rows = [_row(10, 0, 0, Format="Opinion"), _row(20, 0, 0, Format="Opinion"),
            _row(4, 0, 0, Format="Story")]
    stats = es.aggregate(rows, ("Format",))
    cells = {c["value"]: c for c in stats["Format"]}
    assert cells["Opinion"]["n"] == 2
    assert cells["Opinion"]["median"] == 15
    assert cells["Story"]["n"] == 1


def test_aggregate_sorts_by_median_descending():
    rows = [_row(1, 0, 0, Format="A"), _row(1, 0, 0, Format="A"),
            _row(50, 0, 0, Format="B"), _row(50, 0, 0, Format="B")]
    assert [c["value"] for c in es.aggregate(rows, ("Format",))["Format"]] == ["B", "A"]


def test_median_not_mean_decides_the_ranking():
    """Ein viraler Ausreisser darf die Rangfolge nicht drehen: A hat den
    hoeheren Mittelwert, B den hoeheren Median - gewertet wird B."""
    rows = [_row(1, 0, 0, F="A"), _row(1, 0, 0, F="A"), _row(300, 0, 0, F="A"),
            _row(10, 0, 0, F="B"), _row(10, 0, 0, F="B"), _row(12, 0, 0, F="B")]
    cells = es.aggregate(rows, ("F",))["F"]
    assert cells[0]["value"] == "B"
    a = next(c for c in cells if c["value"] == "A")
    assert a["mean"] > cells[0]["mean"]


def test_empty_dimension_value_gets_placeholder():
    stats = es.aggregate([_row(3, 0, 0, Format="")], ("Format",))
    assert stats["Format"][0]["value"] == es.UNSET


def test_unmeasured_rows_are_excluded_entirely():
    assert es.aggregate([_row(Format="Opinion")], ("Format",))["Format"] == []


# --- Gate --------------------------------------------------------------------

def _cells(*ns, step=10):
    """Zellen mit absteigendem Median. step steuert den Abstand, damit die
    Spannen-Pruefung nicht ungewollt zuschlaegt."""
    return [{"value": f"v{i}", "n": n, "median": 100 - i * step,
             "mean": 100 - i * step, "best": 999}
            for i, n in enumerate(ns)]


def test_gate_closed_below_minimum():
    assert es.gate_open(_cells(4, 4), min_n=5) is False


def test_gate_needs_two_full_cells_not_one():
    assert es.gate_open(_cells(20, 1), min_n=5, min_cells=2) is False
    assert es.gate_open(_cells(5, 5), min_n=5, min_cells=2) is True


def test_verdict_is_none_while_gate_closed():
    assert es.verdict(_cells(4, 4), min_n=5) is None


def test_verdict_ignores_undersized_cells():
    """Eine Zelle mit n=1 darf nie als Gewinner oder Verlierer gemeldet werden."""
    cells = _cells(6, 6, 1)
    result = es.verdict(cells, min_n=5, min_cells=2)
    assert result["best"]["value"] == "v0"
    assert result["worst"]["value"] == "v1"
    assert result["spread"] == 10


def test_unset_cell_never_wins():
    """Eine fehlende Property ist keine Entscheidung der Pipeline. lisocon hat
    6 Altposts ohne Matrix-Box - die duerfen nie als Empfehlung erscheinen."""
    cells = _cells(9, 6, 6)
    cells[0]["value"] = es.UNSET
    result = es.verdict(cells, min_n=5, min_cells=2)
    assert result["best"]["value"] == "v1"


def test_unset_does_not_count_toward_the_gate():
    cells = _cells(9, 6)
    cells[0]["value"] = es.UNSET
    assert es.gate_open(cells, min_n=5, min_cells=2) is False


def test_small_spread_blocks_the_verdict():
    """Volle Zellen mit einem Punkt Abstand sind kein Befund - bei Medianen
    von 0 und 1 ist der Sieger eine einzelne Reaktion."""
    cells = _cells(10, 7, step=1)
    assert es.gate_open(cells, min_n=5, min_cells=2) is True
    assert es.verdict(cells, min_n=5, min_cells=2, min_spread=3) is None


def test_sufficient_spread_passes():
    cells = _cells(10, 7, step=4)
    assert es.verdict(cells, min_n=5, min_cells=2, min_spread=3)["spread"] == 4


def test_shortfall_counts_missing_posts():
    assert es.shortfall(_cells(3, 2), min_n=5, min_cells=2) == 2 + 3
    assert es.shortfall(_cells(9, 9), min_n=5, min_cells=2) == 0


def test_shortfall_handles_single_cell():
    assert es.shortfall(_cells(5), min_n=5, min_cells=2) == 5


# --- Report ------------------------------------------------------------------

def test_report_marks_closed_gate_and_shows_all_cells():
    stats = es.aggregate(
        [_row(10, 0, 0, Format="Opinion"), _row(4, 0, 0, Format="Story")], ("Format",))
    text = "\n".join(es.report_lines(stats))
    assert "noch nicht auswertbar" in text
    assert "Opinion" in text and "Story" in text


def test_report_names_the_leader_once_gate_opens():
    rows = ([_row(20, 0, 0, Format="Opinion")] * 5
            + [_row(2, 0, 0, Format="Story")] * 5)
    text = "\n".join(es.report_lines(es.aggregate(rows, ("Format",))))
    assert "auswertbar" in text and "Opinion liegt vorn" in text


def test_report_distinguishes_thin_sample_from_thin_spread():
    """Zwei verschiedene Gruende, das Gate zu lassen - der Report muss sagen
    welcher, sonst wartet man auf Posts, die nichts aendern."""
    thin_sample = es.aggregate([_row(30, 0, 0, F="A"), _row(1, 0, 0, F="B")], ("F",))
    assert "es fehlen" in "\n".join(es.report_lines(thin_sample))

    rows = [_row(2, 0, 0, F="A")] * 5 + [_row(1, 0, 0, F="B")] * 5
    text = "\n".join(es.report_lines(es.aggregate(rows, ("F",))))
    assert "Abstand nicht" in text and "es fehlen" not in text
