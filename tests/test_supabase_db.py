"""Tests for the Supabase PostgREST wrapper. Pure, requests mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import supabase_db


def _post(url="https://x.com/p/1", influencer="Alice", text="body"):
    return {
        "post_url": url,
        "influencer": influencer,
        "post_text": text,
        "date": "2026-06-01T10:00:00+00:00",
        "engagement": {"likes": 5, "comments": 2, "shares": 1},
    }


def test_upsert_posts_maps_rows_and_source(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=201)
    with patch("tools.supabase_db.requests.post", return_value=resp) as mock_post:
        count = supabase_db.upsert_posts([_post()], source="linkedin")
    assert count == 1
    body = mock_post.call_args.kwargs["json"]
    assert body[0]["post_url"] == "https://x.com/p/1"
    assert body[0]["source"] == "linkedin"
    assert body[0]["likes"] == 5
    assert body[0]["comments"] == 2
    assert body[0]["shares"] == 1
    assert body[0]["post_date"] == "2026-06-01"
    assert "on_conflict=post_url" in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["headers"]["Content-Profile"] == "blog_content_mining"


def test_upsert_posts_skips_rows_without_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=201)
    with patch("tools.supabase_db.requests.post", return_value=resp) as mock_post:
        count = supabase_db.upsert_posts([_post(), {"influencer": "NoUrl"}], source="linkedin")
    assert count == 1
    assert len(mock_post.call_args.kwargs["json"]) == 1


def test_upsert_posts_empty_is_noop(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    with patch("tools.supabase_db.requests.post") as mock_post:
        count = supabase_db.upsert_posts([], source="linkedin")
    assert count == 0
    mock_post.assert_not_called()


def test_get_posts_since_builds_gte_filter(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    rows = [{"post_url": "u", "post_text": "t"}]
    resp = MagicMock(status_code=200)
    resp.json.return_value = rows
    with patch("tools.supabase_db.requests.get", return_value=resp) as mock_get:
        out = supabase_db.get_posts_since(7)
    assert out == rows
    params = mock_get.call_args.kwargs["params"]
    assert params["select"] == "*"
    assert params["post_date"].startswith("gte.")
    assert mock_get.call_args.kwargs["headers"]["Accept-Profile"] == "blog_content_mining"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    import pytest
    with pytest.raises(RuntimeError):
        supabase_db.upsert_posts([_post()], source="linkedin")
