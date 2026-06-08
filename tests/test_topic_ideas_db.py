"""Tests for the Topic-Ideas Notion DB layer. requests mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_ideas_db
from tools.topic_clusterer import ThemeCandidate


def _cand():
    return ThemeCandidate(
        theme_label="AI SDR adoption",
        support_count=4,
        sample_influencers=["Alice", "Bob"],
        blog_score=82,
        suggested_title_en="Why AI SDRs Fail Without RevOps",
        suggested_title_de="Warum AI-SDRs ohne RevOps scheitern",
        keyword_en="ai sdr",
        keyword_de="ai sdr",
        supporting_post_urls=["https://x/1", "https://x/2"],
    )


def test_write_candidates_maps_properties(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setenv("TOPIC_IDEAS_DB_ID", "db123")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.ok = True
    with patch("tools.topic_ideas_db.requests.post", return_value=resp) as mock_post:
        n = topic_ideas_db.write_candidates([_cand()])
    assert n == 1
    payload = mock_post.call_args.kwargs["json"]
    props = payload["properties"]
    assert props["Title"]["title"][0]["text"]["content"] == "AI SDR adoption"
    assert props["Suggested Title EN"]["rich_text"][0]["text"]["content"] == "Why AI SDRs Fail Without RevOps"
    assert props["Blog Score"]["number"] == 82
    assert props["Cluster Size"]["number"] == 4
    assert props["Status"]["select"]["name"] == "Hub needed"
    assert props["Type"]["select"]["name"] == "Spoke"
    assert props["Language DE"]["checkbox"] is True
    assert props["Language EN"]["checkbox"] is True
    assert "https://x/1" in props["Supporting Posts"]["rich_text"][0]["text"]["content"]


def test_write_candidates_empty_is_noop(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setenv("TOPIC_IDEAS_DB_ID", "db123")
    with patch("tools.topic_ideas_db.requests.post") as mock_post:
        n = topic_ideas_db.write_candidates([])
    assert n == 0
    mock_post.assert_not_called()


def test_get_recent_idea_titles_extracts_titles(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setenv("TOPIC_IDEAS_DB_ID", "db123")
    resp = MagicMock(status_code=200)
    resp.json.return_value = {
        "results": [
            {"properties": {"Title": {"title": [{"plain_text": "Theme A"}]},
                            "Suggested Title EN": {"rich_text": [{"plain_text": "Title A"}]}}},
        ],
        "has_more": False,
    }
    resp.raise_for_status = MagicMock()
    with patch("tools.topic_ideas_db.requests.post", return_value=resp):
        titles = topic_ideas_db.get_recent_idea_titles(limit=20)
    assert "Theme A" in titles
    assert "Title A" in titles
