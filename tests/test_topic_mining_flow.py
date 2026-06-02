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
