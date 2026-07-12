"""Taste-loop: Notion->Supabase decision sync + taste corpus reader."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import topic_decisions_db
from tools.topic_decisions_db import _to_decision_row, get_taste_corpus, sync_topic_decisions

NOW = "2026-07-12T10:00:00+00:00"


def _page(status, classification="", created="2026-07-10T07:25:00.000Z",
          edited="2026-07-12T09:30:00.000Z"):
    def rt(s):
        return {"rich_text": [{"plain_text": s}]}
    return {
        "id": "39b1617b-1baf-0000-0000-000000000001",
        "created_time": created,
        "last_edited_time": edited,
        "properties": {
            "Status": {"select": {"name": status} if status else None},
            "Classification": {"select": {"name": classification} if classification else None},
            "Title": {"title": [{"plain_text": "Lesbarer Titel"}]},
            "Suggested Title DE": rt("DE-Titel"),
            "Suggested Title EN": rt("EN title"),
            "Keyword DE": rt("kw de"),
            "Keyword EN": rt("kw en"),
            "Blog Score": {"number": 85},
            "Cluster Size": {"number": 4},
            "Source Influencers": rt("A, B"),
            "Parent Hub URL": {"url": "https://x/hub/"},
        },
    }


def test_picked_statuses_map_to_picked_richard():
    for st in ("Ready for Generation", "Generating", "Draft", "Published", "Promoted", "Error"):
        row = _to_decision_row(_page(st), NOW)
        assert row["decision"] == "picked", st
        assert row["decision_source"] == "richard"
        assert row["decided_at"] is not None


def test_rejected_with_classifier_reject_is_auto():
    row = _to_decision_row(_page("Rejected", classification="Reject"), NOW)
    assert row["decision"] == "rejected"
    assert row["decision_source"] == "auto_classifier"


def test_rejected_without_classifier_reject_is_richard():
    row = _to_decision_row(_page("Rejected", classification="Spoke-match"), NOW)
    assert row["decision"] == "rejected"
    assert row["decision_source"] == "richard"


def test_pending_statuses_have_no_decided_at():
    for st in ("New", "Hub needed", "Freigabe offen", ""):
        row = _to_decision_row(_page(st), NOW)
        assert row["decision"] == "pending", st
        assert row["decided_at"] is None
        assert row["decision_source"] == ""


def test_learn_flag_cutoff():
    assert _to_decision_row(_page("Rejected", created="2026-07-09T12:00:00.000Z"), NOW)["learn"] is False
    assert _to_decision_row(_page("Rejected", created="2026-07-10T00:00:00.000Z"), NOW)["learn"] is True


def test_field_mapping():
    row = _to_decision_row(_page("Freigabe offen"), NOW)
    assert row["title_de"] == "DE-Titel"
    assert row["blog_score"] == 85
    assert row["cluster_size"] == 4
    assert row["parent_hub_url"] == "https://x/hub/"
    assert row["batch_date"] == "2026-07-10"
    assert row["theme_label"] == "Lesbarer Titel"


def test_sync_upserts_all_rows(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://sb.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sk")
    resp = MagicMock(status_code=201)
    with patch.object(topic_decisions_db, "_fetch_notion_rows",
                      return_value=[_page("Rejected"), _page("Freigabe offen")]), \
         patch("tools.topic_decisions_db.requests.post", return_value=resp) as post:
        n = sync_topic_decisions()
    assert n == 2
    url = post.call_args.args[0]
    assert "topic_decisions" in url and "on_conflict=notion_page_id" in url
    assert len(post.call_args.kwargs["json"]) == 2


def test_taste_corpus_queries_and_falls_back_to_en(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://sb.example")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "sk")
    resp = MagicMock(status_code=200)
    resp.json.return_value = [{"title_de": "DE eins", "title_en": "EN one"},
                              {"title_de": "", "title_en": "EN only"}]
    with patch("tools.topic_decisions_db.requests.get", return_value=resp) as get:
        corpus = get_taste_corpus(limit_each=7)
    assert corpus["picked"] == ["DE eins", "EN only"]
    picked_params = get.call_args_list[0].kwargs["params"]
    rejected_params = get.call_args_list[1].kwargs["params"]
    assert picked_params["decision"] == "eq.picked"
    assert picked_params["learn"] == "is.true"
    assert picked_params["limit"] == "7"
    # Auto-classifier rejects are policy, not taste — only Richard's rejects count.
    assert rejected_params["decision_source"] == "eq.richard"
