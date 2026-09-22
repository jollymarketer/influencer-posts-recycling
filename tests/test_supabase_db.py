"""Tests for the Supabase PostgREST wrapper. Pure, requests mocked."""
import os
import sys
from datetime import datetime, timedelta, timezone
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
    # Seit 19.08.2026 ist der Schluessel (client, post_url), siehe
    # test_client_scoping_supabase.py.
    assert "on_conflict=client,post_url" in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["headers"]["Content-Profile"] == "blog_content_mining"


def test_upsert_posts_skips_rows_without_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=201)
    with patch("tools.supabase_db.requests.post", return_value=resp) as mock_post:
        count = supabase_db.upsert_posts([_post(), {"influencer": "NoUrl"}], source="linkedin")
    assert count == 1
    assert len(mock_post.call_args.kwargs["json"]) == 1
    assert mock_post.call_args.kwargs["json"][0]["influencer"] == "Alice"


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
    expected = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    assert params["post_date"] == f"gte.{expected}"
    assert mock_get.call_args.kwargs["headers"]["Accept-Profile"] == "blog_content_mining"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    import pytest
    with pytest.raises(RuntimeError):
        supabase_db.upsert_posts([_post()], source="linkedin")


def test_missing_url_raises(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    import pytest
    with pytest.raises(RuntimeError):
        supabase_db.upsert_posts([_post()], source="linkedin")


def test_to_row_traegt_die_achse():
    row = supabase_db._to_row(_post(), "linkedin_search", axis="ki_im_gtm")
    assert row["axis"] == "ki_im_gtm"
    assert row["axis_classified_at"]


def test_to_row_ohne_achse_laesst_die_spalte_weg():
    """Ein mitgeschicktes null wuerde unter resolution=merge-duplicates eine
    schon klassifizierte Zeile beim naechsten Scrape wieder leeren."""
    row = supabase_db._to_row(_post(), "linkedin")
    assert "axis" not in row
    assert "axis_classified_at" not in row


def test_get_unclassified_filtert_auf_zeitstempel_nicht_auf_achse(monkeypatch):
    """'Passt in keine Achse' ist axis=null MIT Zeitstempel und darf nicht in
    jedem Lauf erneut bezahlt werden."""
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=200)
    resp.json.return_value = []
    with patch("tools.supabase_db.requests.get", return_value=resp) as mock_get:
        supabase_db.get_unclassified_posts(90, limit=7)
    params = mock_get.call_args.kwargs["params"]
    assert params["axis_classified_at"] == "is.null"
    assert "axis" not in params
    assert params["source"] == "in.(linkedin,substack)"
    assert params["limit"] == "7"


def test_set_axis_schreibt_none_mit_zeitstempel(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=204)
    with patch("tools.supabase_db.requests.patch", return_value=resp) as mock_patch:
        supabase_db.set_axis("https://x.com/p/1", None)
    body = mock_patch.call_args.kwargs["json"]
    assert body["axis"] is None
    assert body["axis_classified_at"]
    assert mock_patch.call_args.kwargs["params"]["post_url"] == "eq.https://x.com/p/1"


def test_axis_distribution_zaehlt_null_eigen(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://db.example.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"axis": "ki_im_gtm"}, {"axis": None}, {"axis": "ki_im_gtm"}]
    with patch("tools.supabase_db.requests.get", return_value=resp):
        out = supabase_db.axis_distribution(30)
    assert out == {"ki_im_gtm": 2, "null": 1}
