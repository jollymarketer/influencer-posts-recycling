"""Tests for the slate rescore floor (run_slate.rows_to_rescore).

Der Pool wurde bei jedem Slate-Lauf komplett neu mit Sonnet gescored, obwohl jeder
Eintrag Score und Klassifikation gespeichert hat. Der Floor bewertet nur noch, was
nahe genug am Gate liegt. Diese Tests halten die zwei Eigenschaften fest, die dabei
schiefgehen koennen: nie gescorte Zeilen duerfen nicht durchrutschen, und floor=0
muss die alte Vollbewertung wiederherstellen.
"""
from run_slate import rows_to_rescore


def _row(url, score):
    return {"post_url": url, "score_total": score}


def test_floor_splits_at_the_threshold():
    rows = [_row("a", 32), _row("b", 20), _row("c", 19), _row("d", 7)]
    to_score, dormant = rows_to_rescore(rows, 20)
    assert [r["post_url"] for r in to_score] == ["a", "b"]
    assert [r["post_url"] for r in dormant] == ["c", "d"]


def test_never_scored_rows_always_get_scored():
    """Ein frisch gescrapter Post hat score_total None und muss mitkommen,
    sonst erreicht er nie einen Slate."""
    rows = [_row("neu", None), _row("schwach", 5)]
    to_score, dormant = rows_to_rescore(rows, 20)
    assert [r["post_url"] for r in to_score] == ["neu"]
    assert [r["post_url"] for r in dormant] == ["schwach"]


def test_floor_zero_scores_everything():
    """Abschalt-Pfad: ohne Floor verhaelt sich der Lauf wie vor der Aenderung."""
    rows = [_row("a", 1), _row("b", None), _row("c", 30)]
    to_score, dormant = rows_to_rescore(rows, 0)
    assert len(to_score) == 3
    assert dormant == []


def test_split_keeps_every_row():
    """Keine Zeile darf verloren gehen - sonst faellt ein Kandidat still aus dem Pool."""
    rows = [_row(str(i), i % 35) for i in range(50)]
    to_score, dormant = rows_to_rescore(rows, 20)
    assert len(to_score) + len(dormant) == len(rows)
    assert {r["post_url"] for r in to_score} | {r["post_url"] for r in dormant} == {
        r["post_url"] for r in rows
    }
