"""Tests for the box-fit re-rank. The anthropic client is mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import post_scorer

POSTS = [
    {"influencer": "A", "post_text": "How to compare GTM agencies."},
    {"influencer": "B", "post_text": "My morning routine."},
    {"influencer": "C", "post_text": "Buy vs build for outbound."},
]
BOX = ("Perspective", "Selection")


def _mock(reply):
    resp = MagicMock()
    resp.content = [MagicMock(text=reply)]
    c = MagicMock()
    c.messages.create.return_value = resp
    return c


def test_picks_highest_fit_at_or_above_threshold():
    reply = '[{"index": 0, "fit": 7}, {"index": 1, "fit": 2}, {"index": 2, "fit": 9}]'
    with patch.object(post_scorer, "client", _mock(reply)):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) == 2


def test_returns_none_when_nothing_reaches_threshold():
    reply = '[{"index": 0, "fit": 5}, {"index": 1, "fit": 1}, {"index": 2, "fit": 4}]'
    with patch.object(post_scorer, "client", _mock(reply)):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) is None


def test_returns_none_on_api_error():
    c = MagicMock()
    c.messages.create.side_effect = RuntimeError("down")
    with patch.object(post_scorer, "client", c):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) is None


def test_returns_none_on_garbage_json():
    with patch.object(post_scorer, "client", _mock("not json")):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) is None


def test_ignores_out_of_range_indices():
    reply = '[{"index": 99, "fit": 10}, {"index": 1, "fit": 8}]'
    with patch.object(post_scorer, "client", _mock(reply)):
        assert post_scorer.rank_box_fit(POSTS, BOX, ["Comparison"]) == 1
