"""Schritt 2b: keyword search as additional daily source, gated by
FEATURES["keyword_source_daily"] (lisocon on, jolly off). Scraper mocked."""
from types import SimpleNamespace
from unittest.mock import patch

import run_research


def _cfg(flag_on: bool):
    return SimpleNamespace(
        FEATURES={"keyword_source_daily": flag_on},
        DAILY_KEYWORD_SEARCH={
            "keywords": ["CCMS", "Fremdsprachensatz"],
            "max_posts": 10,
            "posted_limit": "week",
        },
    )


def test_flag_off_does_not_call_scraper():
    with patch.object(run_research, "_cfg", _cfg(False)), \
         patch.object(run_research, "scrape_keyword_posts") as sk:
        posts = run_research.scrape_daily_keyword_posts(set(), [])
    sk.assert_not_called()
    assert posts == []


def test_flag_on_merges_and_dedupes():
    scraped = [{"post_url": "https://x/new", "post_text": "t", "influencer": "A"}]
    already = [{"post_url": "https://x/seen"}]
    with patch.object(run_research, "_cfg", _cfg(True)), \
         patch.object(run_research, "scrape_keyword_posts", return_value=scraped) as sk:
        posts = run_research.scrape_daily_keyword_posts({"https://x/notion"}, already)
    assert posts == scraped
    kwargs = sk.call_args.kwargs
    # In-run posts AND notion winner URLs must both be excluded server-side.
    assert kwargs["existing_urls"] == {"https://x/notion", "https://x/seen"}
    assert kwargs["max_posts"] == 10
    assert kwargs["posted_limit"] == "week"
    assert sk.call_args.args[0] == ["CCMS", "Fremdsprachensatz"]


def test_scraper_error_is_non_fatal():
    with patch.object(run_research, "_cfg", _cfg(True)), \
         patch.object(run_research, "scrape_keyword_posts", side_effect=RuntimeError("apify down")):
        posts = run_research.scrape_daily_keyword_posts(set(), [])
    assert posts == []
