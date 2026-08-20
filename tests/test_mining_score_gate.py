"""Tests fuer das Scoring-Gate und den Achsen-Split im Topic Mining.
Kein Modell-, kein Supabase-, kein Notion-Aufruf."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_topic_mining as rtm
from tools.topic_clusterer import ThemeCandidate


def _cfg(gate=False, axes=None, min_score=15):
    return SimpleNamespace(
        NAME="testclient",
        FEATURES={"mining_score_gate": gate},
        MIN_SCORE=min_score,
        KEYWORDS_BY_AXIS=axes,
    )


def _post(url, source="linkedin_search:a1", likes=10):
    return {"post_url": url, "source": source, "influencer": "I",
            "post_text": "text " + url, "likes": likes, "comments": 1, "shares": 0}


def _cand(support=5, label="T"):
    return ThemeCandidate(
        theme_label=label, support_count=support, sample_influencers=["A"],
        suggested_title_en="t", suggested_title_de="t",
        keyword_en="k", keyword_de="k",
    )


# --- Adapter -----------------------------------------------------------------

def test_row_to_post_nests_engagement():
    p = rtm._row_to_post(_post("u1", likes=7))
    assert p["engagement"] == {"likes": 7, "comments": 1, "shares": 0}
    assert p["influencer"] == "I"
    assert p["post_text"] == "text u1"


# --- Scoring-Gate ------------------------------------------------------------

def test_gate_off_does_not_score():
    posts = [_post("u1"), _post("u2")]
    with patch("tools.post_scorer.score_posts") as mock_score:
        out = rtm._apply_score_gate(posts, _cfg(gate=False))
    mock_score.assert_not_called()
    assert out == posts


def test_gate_filters_below_min_score():
    posts = [_post("u1"), _post("u2")]

    def fake_score(adapted, recent_drafts=None):
        assert all("engagement" in p for p in adapted)
        return [{**adapted[0], "score": 20}, {**adapted[1], "score": 10}]

    with patch("tools.post_scorer.score_posts", side_effect=fake_score):
        out = rtm._apply_score_gate(posts, _cfg(gate=True, min_score=15))
    assert [p["post_url"] for p in out] == ["u1"]


# --- Achsen-Split ------------------------------------------------------------

def test_split_by_axis_groups_by_source():
    cfg = _cfg(axes={"a1": ["k"], "a2": ["k"]})
    posts = [_post("u1", "linkedin_search:a1"), _post("u2", "linkedin_search:a2"),
             _post("u3", "linkedin"), _post("u4", "linkedin_search:unbekannt")]
    groups = rtm._split_by_axis(posts, cfg)
    assert {p["post_url"] for p in groups["a1"]} == {"u1"}
    assert {p["post_url"] for p in groups["a2"]} == {"u2"}
    assert {p["post_url"] for p in groups[None]} == {"u3", "u4"}


def test_split_without_axes_config_is_single_pot():
    posts = [_post("u1"), _post("u2")]
    groups = rtm._split_by_axis(posts, _cfg(axes=None))
    assert list(groups) == [None]
    assert groups[None] == posts


# --- Orchestrierung ----------------------------------------------------------

def test_mining_per_axis_passes_achse_and_per_axis_top_n():
    cfg = _cfg(axes={"a1": ["k"], "a2": ["k"]})
    posts = ([_post(f"u{i}", "linkedin_search:a1") for i in range(3)]
             + [_post(f"v{i}", "linkedin_search:a2") for i in range(3)])
    with patch.object(rtm, "get_posts_since", return_value=posts), \
         patch.object(rtm, "get_recent_idea_titles", return_value=[]), \
         patch.object(rtm, "get_taste_corpus", return_value=None), \
         patch.object(rtm, "cluster_topics", return_value=[_cand()]), \
         patch.object(rtm, "filter_candidates", side_effect=lambda c, **kw: c) as mock_filter, \
         patch.object(rtm, "write_candidates", return_value=1) as mock_write:
        rtm.run_topic_mining(cfg=cfg)
    achsen = {c.kwargs.get("achse") for c in mock_write.call_args_list}
    assert achsen == {"a1", "a2"}
    top_ns = {c.kwargs["top_n"] for c in mock_filter.call_args_list}
    assert top_ns == {rtm.TOP_N_PER_AXIS}


def test_mining_without_axes_writes_single_pot_without_achse():
    cfg = _cfg(axes=None)
    posts = [_post(f"u{i}", "linkedin") for i in range(3)]
    with patch.object(rtm, "get_posts_since", return_value=posts), \
         patch.object(rtm, "get_recent_idea_titles", return_value=[]), \
         patch.object(rtm, "get_taste_corpus", return_value=None), \
         patch.object(rtm, "cluster_topics", return_value=[_cand()]), \
         patch.object(rtm, "write_candidates", return_value=1) as mock_write:
        rtm.run_topic_mining(cfg=cfg)
    assert mock_write.call_count == 1
    assert mock_write.call_args.kwargs.get("achse") is None


def test_mining_gate_runs_before_clustering():
    cfg = _cfg(gate=True, axes=None, min_score=15)
    posts = [_post("u1"), _post("u2"), _post("u3")]

    def fake_score(adapted, recent_drafts=None):
        return [{**p, "score": (20 if p["post_url"] != "u3" else 5)} for p in adapted]

    with patch.object(rtm, "get_posts_since", return_value=posts), \
         patch.object(rtm, "get_recent_idea_titles", return_value=[]), \
         patch.object(rtm, "get_taste_corpus", return_value=None), \
         patch("tools.post_scorer.score_posts", side_effect=fake_score), \
         patch.object(rtm, "cluster_topics", return_value=[_cand()]) as mock_cluster, \
         patch.object(rtm, "write_candidates", return_value=1):
        rtm.run_topic_mining(cfg=cfg)
    clustered = mock_cluster.call_args.args[0]
    assert {p["post_url"] for p in clustered} == {"u1", "u2"}
