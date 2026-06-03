"""Tests for update_with_draft property mapping. _notion_request mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def _run(monkeypatch, **kw):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(page_id="p1", image_prompt="", image_url="", **kw)
    # _notion_request is called multiple times (page PATCH + block append);
    # pick the call carrying the page properties.
    for call in m.call_args_list:
        body = call.kwargs.get("json", {})
        if "properties" in body:
            return body["properties"]
    raise AssertionError("no _notion_request call carried 'properties'")


def test_en_draft_written_to_own_property(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="DE text", en_draft="EN text")
    assert props["LinkedIn Draft EN"]["rich_text"][0]["text"]["content"] == "EN text"


def test_de_and_en_truncate_at_3000(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="D" * 3500, en_draft="E" * 3500)
    assert len(props["LinkedIn Draft"]["rich_text"][0]["text"]["content"]) == 3000
    assert len(props["LinkedIn Draft EN"]["rich_text"][0]["text"]["content"]) == 3000


def test_empty_en_draft_omits_property(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="DE text", en_draft="")
    assert "LinkedIn Draft EN" not in props
