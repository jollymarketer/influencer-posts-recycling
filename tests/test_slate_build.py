"""select_slate: 5/5-Quota, Fill+Mark, MIN_SCORE-Gate. Pure Logik."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run_slate import select_slate, MIN_SCORE

CFG = SimpleNamespace(SLATE={"days": (0, 3), "size": 10, "per_persona": 5,
                             "max_age_days": 60, "max_times_slated": 3})


def _cand(url, persona, score):
    return {"post_url": url, "persona": persona, "score": score}


def test_five_five_quota():
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i) for i in range(8)]
              + [_cand(f"a{i}", "anwender", 50 - i) for i in range(8)])
    slate = select_slate(scored, CFG)
    assert len(slate) == 10
    assert sum(1 for c in slate if c["persona"] == "kaeufer") == 5
    assert sum(1 for c in slate if c["persona"] == "anwender") == 5
    assert not any(c.get("fill_marker") for c in slate)


def test_fill_and_mark_when_one_side_short():
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i) for i in range(2)]
              + [_cand(f"a{i}", "anwender", 40 - i) for i in range(10)])
    slate = select_slate(scored, CFG)
    assert len(slate) == 10
    kaeufer = [c for c in slate if c["persona"] == "kaeufer"]
    assert len(kaeufer) == 2
    filled = [c for c in slate if c.get("fill_marker")]
    assert len(filled) == 3  # anwender rows standing in on the kaeufer side


def test_min_score_gate():
    scored = ([_cand(f"k{i}", "kaeufer", 20) for i in range(5)]
              + [_cand(f"a{i}", "anwender", 30) for i in range(5)])
    slate = select_slate(scored, CFG)
    assert all(c["score"] >= MIN_SCORE for c in slate)
    assert all(c["persona"] == "anwender" for c in slate)


def test_sorted_by_score_within_side():
    scored = [_cand("k1", "kaeufer", 30), _cand("k2", "kaeufer", 45),
              _cand("a1", "anwender", 28), _cand("a2", "anwender", 44)]
    slate = select_slate(scored, CFG)
    kaeufer = [c for c in slate if c["persona"] == "kaeufer"]
    assert kaeufer[0]["post_url"] == "k2"
