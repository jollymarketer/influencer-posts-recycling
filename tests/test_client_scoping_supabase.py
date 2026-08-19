"""Mandanten-Trennung im blog_content_mining-Schema (Migration 19.08.2026).

Jede Zeile traegt client, der Primaerschluessel ist (client, post_url), jeder
Lese- und Schreibpfad filtert. Regression: vorher war das Schema implizit
jolly-only, ein SWOT-Lauf waere in Jollys Freitag-Mining gelandet und Jollys
Taste-Korpus haette SWOT kalibriert. requests gemockt, kein Netz.
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import supabase_db, topic_decisions_db
from tools.topic_clusterer import _system_prompt


def _post(url="https://x/p/1"):
    return {"post_url": url, "influencer": "A", "post_text": "t",
            "date": "2026-08-19", "engagement": {"likes": 1, "comments": 2, "shares": 0}}


def test_to_row_traegt_client(monkeypatch):
    monkeypatch.setattr(supabase_db, "_client_name", lambda: "swot")
    row = supabase_db._to_row(_post(), "linkedin_search")
    assert row["client"] == "swot"


def test_upsert_on_conflict_client_und_url(monkeypatch):
    monkeypatch.setattr(supabase_db, "_client_name", lambda: "swot")
    monkeypatch.setenv("SUPABASE_URL", "https://sb.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=201)
    with patch("tools.supabase_db.requests.post", return_value=resp) as mock_post:
        n = supabase_db.upsert_posts([_post()], source="linkedin_search")
    assert n == 1
    url = mock_post.call_args.args[0]
    # on_conflict MUSS beide Schluesselspalten nennen, sonst kapert der zweite
    # Mandant die Zeile des ersten (merge-duplicates).
    assert "on_conflict=client,post_url" in url


def test_get_posts_since_filtert_client(monkeypatch):
    monkeypatch.setattr(supabase_db, "_client_name", lambda: "swot")
    monkeypatch.setenv("SUPABASE_URL", "https://sb.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=200)
    resp.json.return_value = []
    with patch("tools.supabase_db.requests.get", return_value=resp) as mock_get:
        supabase_db.get_posts_since(7)
    params = mock_get.call_args.kwargs["params"]
    assert params["client"] == "eq.swot"


def test_taste_corpus_filtert_client(monkeypatch):
    monkeypatch.setattr(topic_decisions_db, "_client_name", lambda: "swot")
    monkeypatch.setenv("SUPABASE_URL", "https://sb.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    resp = MagicMock(status_code=200)
    resp.json.return_value = []
    with patch("tools.topic_decisions_db.requests.get", return_value=resp) as mock_get:
        topic_decisions_db.get_taste_corpus()
    for call in mock_get.call_args_list:
        assert call.kwargs["params"]["client"] == "eq.swot"


def test_decision_row_traegt_client(monkeypatch):
    monkeypatch.setattr(topic_decisions_db, "_client_name", lambda: "swot")
    page = {"id": "pg1", "created_time": "2026-08-19T00:00:00Z",
            "last_edited_time": "2026-08-19T00:00:00Z",
            "properties": {"Status": {"select": {"name": "Rejected"}},
                           "Title": {"title": []}}}
    row = topic_decisions_db._to_decision_row(page, "2026-08-19T00:00:00Z")
    assert row["client"] == "swot"


def test_cluster_rolle_je_mandant(monkeypatch):
    from clients import load_client

    class _Cfg:
        NAME = "swot"
        TOKENS = {"TOPIC_CLUSTER_ROLE": "role-swot"}

    monkeypatch.setattr("clients.load_client", lambda: _Cfg)
    load_client.cache_clear()
    try:
        assert _system_prompt() == "role-swot"
    finally:
        load_client.cache_clear()


def test_cluster_rolle_fehlt_bricht_hart(monkeypatch):
    from clients import load_client

    class _Cfg:
        NAME = "lisocon"
        TOKENS = {}

    monkeypatch.setattr("clients.load_client", lambda: _Cfg)
    load_client.cache_clear()
    try:
        import pytest
        with pytest.raises(RuntimeError, match="TOPIC_CLUSTER_ROLE"):
            _system_prompt()
    finally:
        load_client.cache_clear()
