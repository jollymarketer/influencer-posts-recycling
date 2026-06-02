"""Tests for topic clustering. Claude client mocked — no API calls."""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_clusterer
from tools.topic_clusterer import ThemeCandidate, _build_user_prompt, _parse_clusters, filter_candidates


def _raw(themes):
    return json.dumps(themes)


SAMPLE = [
    {
        "theme_label": "AI SDR adoption",
        "support_count": 4,
        "sample_influencers": ["Alice", "Bob"],
        "blog_score": 82,
        "suggested_title_en": "Why AI SDRs Fail Without RevOps",
        "suggested_title_de": "Warum AI-SDRs ohne RevOps scheitern",
        "keyword_en": "ai sdr",
        "keyword_de": "ai sdr",
        "supporting_post_urls": ["https://x/1", "https://x/2"],
    },
    {
        "theme_label": "Cold email deliverability",
        "support_count": 2,
        "sample_influencers": ["Cara"],
        "blog_score": 55,
        "suggested_title_en": "Deliverability in 2026",
        "suggested_title_de": "Zustellbarkeit 2026",
        "keyword_en": "email deliverability",
        "keyword_de": "zustellbarkeit",
        "supporting_post_urls": ["https://x/3"],
    },
]


def test_parse_clusters_plain_json():
    out = _parse_clusters(_raw(SAMPLE))
    assert len(out) == 2
    assert isinstance(out[0], ThemeCandidate)
    assert out[0].theme_label == "AI SDR adoption"
    assert out[0].blog_score == 82


def test_parse_clusters_strips_code_fence():
    fenced = "```json\n" + _raw(SAMPLE) + "\n```"
    out = _parse_clusters(fenced)
    assert len(out) == 2


def test_parse_clusters_bad_json_returns_empty():
    assert _parse_clusters("not json at all") == []


def test_filter_candidates_threshold_and_topn():
    cands = _parse_clusters(_raw(SAMPLE))
    out = filter_candidates(cands, threshold=70, top_n=5, recent_titles=[])
    assert len(out) == 1
    assert out[0].theme_label == "AI SDR adoption"


def test_filter_candidates_dedup_case_insensitive_substring():
    cands = _parse_clusters(_raw(SAMPLE))
    out = filter_candidates(
        cands, threshold=50, top_n=5,
        recent_titles=["why ai sdrs fail without revops"],
    )
    labels = [c.theme_label for c in out]
    assert "AI SDR adoption" not in labels
    assert "Cold email deliverability" in labels


def test_filter_candidates_topn_caps_after_sort():
    many = []
    for i in range(10):
        t = dict(SAMPLE[0])
        t["blog_score"] = 70 + i
        t["theme_label"] = f"Theme {i}"
        t["suggested_title_en"] = f"Title {i}"
        many.append(t)
    cands = _parse_clusters(_raw(many))
    out = filter_candidates(cands, threshold=70, top_n=5, recent_titles=[])
    assert len(out) == 5
    assert out[0].blog_score == 79


def test_filter_candidates_short_label_does_not_false_dedup():
    # A distinct theme whose short label ("Cold email") is a substring of an
    # unrelated long recent title must NOT be dropped.
    t = {
        "theme_label": "Cold email",
        "support_count": 3,
        "sample_influencers": ["X"],
        "blog_score": 80,
        "suggested_title_en": "Cold Email Copywriting Tactics That Convert",
        "suggested_title_de": "Cold-Email-Copywriting das konvertiert",
        "keyword_en": "cold email copywriting",
        "keyword_de": "cold email copywriting",
        "supporting_post_urls": ["https://x/9"],
    }
    cands = _parse_clusters(_raw([t]))
    out = filter_candidates(
        cands, threshold=50, top_n=5,
        recent_titles=["Cold email deliverability best practices in 2026"],
    )
    assert len(out) == 1  # distinct theme kept, not false-deduped


def test_cluster_topics_returns_empty_for_too_few_posts():
    out = topic_clusterer.cluster_topics([{"post_text": "x"}], recent_titles=[])
    assert out == []


def test_cluster_topics_calls_claude_and_parses():
    posts = [{"influencer": "A", "post_text": "p", "engagement": {"likes": 1, "comments": 0, "shares": 0}}] * 3
    fake = MagicMock()
    fake.content = [MagicMock(text=_raw(SAMPLE))]
    with patch("tools.topic_clusterer.client") as mock_client:
        mock_client.messages.create.return_value = fake
        out = topic_clusterer.cluster_topics(posts, recent_titles=[])
    assert mock_client.messages.create.called
    assert mock_client.messages.create.call_args.kwargs["model"] == "claude-sonnet-4-6"
    assert len(out) == 2


def test_build_user_prompt_reads_flat_supabase_row_engagement():
    # Supabase rows are FLAT (no nested "engagement"); the prompt must still read metrics.
    flat = [{"influencer": "A", "post_url": "https://x/1", "post_text": "body",
             "likes": 42, "comments": 7, "shares": 3}]
    prompt = _build_user_prompt(flat, recent_titles=[])
    assert "likes=42" in prompt
    assert "comments=7" in prompt
