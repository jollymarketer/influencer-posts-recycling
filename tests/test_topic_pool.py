"""Tests for the topic candidate pool wrapper. Pure, requests mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_pool


def _env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")


def test_upsert_candidates_on_conflict_post_url(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=201)
    rows = [{"post_url": "https://x.com/p/1", "client": "lisocon", "state": "pool"}]
    with patch("tools.topic_pool.requests.post", return_value=resp) as mock_post:
        n = topic_pool.upsert_candidates(rows)
    assert n == 1
    assert "topic_candidates?on_conflict=post_url" in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["headers"]["Content-Profile"] == "blog_content_mining"


def test_get_pool_urls_returns_all_states(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "https://x.com/p/1"}, {"post_url": "https://x.com/p/2"}]
    with patch("tools.topic_pool.requests.get", return_value=resp) as mock_get:
        urls = topic_pool.get_pool_urls("lisocon")
    assert urls == {"https://x.com/p/1", "https://x.com/p/2"}
    params = mock_get.call_args.kwargs["params"]
    assert params["client"] == "eq.lisocon"
    assert "state" not in params  # every state counts as dedup memory


def test_get_candidates_filters_states(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "u", "state": "pool"}]
    with patch("tools.topic_pool.requests.get", return_value=resp) as mock_get:
        rows = topic_pool.get_candidates("lisocon", ["pool", "slated"])
    assert rows[0]["post_url"] == "u"
    assert mock_get.call_args.kwargs["params"]["state"] == "in.(pool,slated)"


def test_set_state_patches_by_url_list(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=204)
    with patch("tools.topic_pool.requests.patch", return_value=resp) as mock_patch:
        topic_pool.set_state(["https://x.com/p/1"], "picked")
    body = mock_patch.call_args.kwargs["json"]
    assert body == {"state": "picked"}
    assert mock_patch.call_args.kwargs["params"]["post_url"] == 'in.("https://x.com/p/1")'


def test_unslate_and_strike_retires_at_threshold(monkeypatch):
    _env(monkeypatch)
    get_resp = MagicMock(status_code=200)
    get_resp.json.return_value = [
        {"post_url": "https://x.com/p/1", "times_slated": 2},
        {"post_url": "https://x.com/p/2", "times_slated": 0},
    ]
    patch_resp = MagicMock(status_code=204)
    with patch("tools.topic_pool.requests.get", return_value=get_resp), \
         patch("tools.topic_pool.requests.patch", return_value=patch_resp) as mock_patch:
        topic_pool.unslate_and_strike(
            ["https://x.com/p/1", "https://x.com/p/2"], max_times_slated=3)
    bodies = [c.kwargs["json"] for c in mock_patch.call_args_list]
    assert {"times_slated": 3, "state": "retired"} in bodies
    assert {"times_slated": 1, "state": "pool"} in bodies


def test_retire_aged_uses_cutoff_and_active_states(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "u"}]
    with patch("tools.topic_pool.requests.patch", return_value=resp) as mock_patch:
        n = topic_pool.retire_aged("lisocon", max_age_days=60)
    assert n == 1
    params = mock_patch.call_args.kwargs["params"]
    assert params["client"] == "eq.lisocon"
    assert params["state"] == "in.(pool,slated)"
    assert params["first_seen_at"].startswith("lt.")
    assert mock_patch.call_args.kwargs["json"] == {"state": "retired"}


def test_revive_picked_resets_cycle(monkeypatch):
    _env(monkeypatch)
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"post_url": "u"}]
    with patch("tools.topic_pool.requests.patch", return_value=resp) as mock_patch:
        n = topic_pool.revive_picked("lisocon", min_age_days=42)
    assert n == 1
    params = mock_patch.call_args.kwargs["params"]
    assert params["client"] == "eq.lisocon"
    assert params["state"] == "eq.picked"
    assert params["last_slated_at"].startswith("lt.")
    body = mock_patch.call_args.kwargs["json"]
    assert body["state"] == "pool"
    assert body["times_slated"] == 0
    assert "first_seen_at" in body


def test_meta_roundtrip(monkeypatch):
    _env(monkeypatch)
    get_resp = MagicMock(status_code=200)
    get_resp.json.return_value = [{"key": "last_slate_at_lisocon", "value": "2026-07-16"}]
    post_resp = MagicMock(status_code=201)
    with patch("tools.topic_pool.requests.get", return_value=get_resp):
        assert topic_pool.get_meta("last_slate_at_lisocon") == "2026-07-16"
    with patch("tools.topic_pool.requests.post", return_value=post_resp) as mock_post:
        topic_pool.set_meta("last_slate_at_lisocon", "2026-07-17")
    assert "engine_meta?on_conflict=key" in mock_post.call_args.args[0]
