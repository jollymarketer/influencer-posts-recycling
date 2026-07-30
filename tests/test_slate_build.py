"""select_slate: 5/5-Quota, Fill+Mark, MIN_SCORE-Gate, Themen-Cap. Pure Logik."""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from run_slate import select_slate, topic_cluster, MIN_SCORE

CFG = SimpleNamespace(SLATE={"days": (0,), "size": 10, "per_persona": 5,
                             "max_age_days": 60, "max_times_slated": 3})

CAPPED = SimpleNamespace(
    SLATE=CFG.SLATE,
    TOPIC_CLUSTER_CAP=2,
    TOPIC_CLUSTERS=[{"id": "mvo", "keywords": ("maschinenverordnung",)},
                    {"id": "terminologie", "keywords": ("terminologie",)}],
)


def _cand(url, persona, score, angle=""):
    return {"post_url": url, "persona": persona, "score": score,
            "topic_angle_de": angle}


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


# --- Themen-Cap (Kundenfeedback Jae 2026-07-30) ------------------------------

def test_cluster_of_candidate():
    assert topic_cluster(_cand("x", "kaeufer", 40,
                               "Die EU-Maschinenverordnung ab 20.01.2027"), CAPPED) == "mvo"
    assert topic_cluster(_cand("x", "kaeufer", 40, "Etwas ganz anderes"), CAPPED) == ""
    # Ohne Cluster-Konfiguration ist alles clusterlos - Jolly-Pfad bleibt heil.
    assert topic_cluster(_cand("x", "kaeufer", 40, "Maschinenverordnung"), CFG) == ""


def test_cluster_cap_limits_one_topic_per_side():
    """Der Live-Fall vom 30.07.: 6 MVO-Kandidaten fuehren die Kaeufer-Seite an."""
    scored = ([_cand(f"mvo{i}", "kaeufer", 50 - i, "EU-Maschinenverordnung 2027")
               for i in range(6)]
              + [_cand(f"k{i}", "kaeufer", 30 - i, "Durchlaufzeit ueber Sprachen")
                 for i in range(4)]
              + [_cand(f"a{i}", "anwender", 40 - i, "Korrekturschleifen im Layout")
                 for i in range(5)])
    slate = select_slate(scored, CAPPED)
    kaeufer = [c for c in slate if c["persona"] == "kaeufer"]
    assert len(kaeufer) == 5
    assert sum(1 for c in kaeufer if c["post_url"].startswith("mvo")) == 2
    # Die zwei staerksten MVO-Winkel gewinnen, nicht irgendwelche zwei.
    assert [c["post_url"] for c in kaeufer[:2]] == ["mvo0", "mvo1"]
    assert not any(c.get("cluster_overflow") for c in slate)


def test_cluster_cap_is_per_persona_side():
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i, "Maschinenverordnung") for i in range(5)]
              + [_cand(f"a{i}", "anwender", 40 - i, "Maschinenverordnung") for i in range(5)])
    slate = select_slate(scored, CAPPED)
    assert sum(1 for c in slate if c["persona"] == "kaeufer"
               and not c.get("cluster_overflow")) == 2
    assert sum(1 for c in slate if c["persona"] == "anwender"
               and not c.get("cluster_overflow")) == 2


def test_uncategorised_candidates_are_not_capped():
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i, f"Freier Winkel {i}") for i in range(5)]
              + [_cand(f"a{i}", "anwender", 40 - i, f"Anderer Winkel {i}") for i in range(5)])
    slate = select_slate(scored, CAPPED)
    assert len(slate) == 10
    assert not any(c.get("cluster_overflow") for c in slate)


def test_cluster_cap_relaxes_instead_of_starving_the_slate():
    """Pool nur aus einem Cluster: lieber volles Slate mit Marker als leeres."""
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i, "Maschinenverordnung") for i in range(6)]
              + [_cand(f"a{i}", "anwender", 40 - i, "Maschinenverordnung") for i in range(6)])
    slate = select_slate(scored, CAPPED)
    assert len(slate) == 10
    overflow = [c for c in slate if c.get("cluster_overflow")]
    assert len(overflow) == 6
    assert all(c.get("fill_marker") for c in overflow)


def test_cap_zero_disables_the_gate():
    cfg = SimpleNamespace(SLATE=CFG.SLATE, TOPIC_CLUSTER_CAP=0,
                          TOPIC_CLUSTERS=CAPPED.TOPIC_CLUSTERS)
    scored = ([_cand(f"k{i}", "kaeufer", 50 - i, "Maschinenverordnung") for i in range(5)]
              + [_cand(f"a{i}", "anwender", 40 - i, "Maschinenverordnung") for i in range(5)])
    slate = select_slate(scored, cfg)
    assert len(slate) == 10
    assert not any(c.get("cluster_overflow") for c in slate)
