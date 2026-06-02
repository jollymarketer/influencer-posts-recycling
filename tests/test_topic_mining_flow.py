"""Tests for persistence hook + Friday trigger + mining orchestration."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_research


def test_persist_scraped_posts_tags_source_and_is_nonfatal():
    li = [{"post_url": "a", "influencer": "A"}]
    ss = [{"post_url": "b", "influencer": "B"}]
    with patch("run_research.upsert_posts") as mock_up:
        run_research.persist_scraped_posts(li, ss)
    sources = {c.kwargs.get("source") or c.args[1] for c in mock_up.call_args_list}
    assert sources == {"linkedin", "substack"}


def test_persist_scraped_posts_swallows_errors():
    with patch("run_research.upsert_posts", side_effect=RuntimeError("db down")):
        run_research.persist_scraped_posts([{"post_url": "a"}], [])


import run_topic_mining
from tools.topic_clusterer import ThemeCandidate


def _cand(score, label="T"):
    return ThemeCandidate(
        theme_label=label, support_count=3, sample_influencers=["A"],
        blog_score=score, suggested_title_en="t", suggested_title_de="t",
        keyword_en="k", keyword_de="k", supporting_post_urls=["u"],
    )


def test_mining_skips_when_too_few_posts():
    with patch("run_topic_mining.get_posts_since", return_value=[{"post_url": "a"}]), \
         patch("run_topic_mining.cluster_topics") as mock_cluster, \
         patch("run_topic_mining.write_candidates") as mock_write:
        run_topic_mining.run_topic_mining()
    mock_cluster.assert_not_called()
    mock_write.assert_not_called()


def test_mining_filters_and_writes_top5():
    posts = [{"post_url": str(i)} for i in range(5)]
    cands = [_cand(90, "A"), _cand(50, "B"), _cand(75, "C")]
    with patch("run_topic_mining.get_posts_since", return_value=posts), \
         patch("run_topic_mining.get_recent_idea_titles", return_value=[]), \
         patch("run_topic_mining.cluster_topics", return_value=cands), \
         patch("run_topic_mining.write_candidates") as mock_write:
        run_topic_mining.run_topic_mining()
    written = mock_write.call_args.args[0]
    labels = [c.theme_label for c in written]
    assert labels == ["A", "C"]
