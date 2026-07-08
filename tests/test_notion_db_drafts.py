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


def test_de_and_en_truncate_at_notion_limit_2000(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="D" * 3500, en_draft="E" * 3500)
    assert len(props["LinkedIn Draft"]["rich_text"][0]["text"]["content"]) == 2000
    assert len(props["LinkedIn Draft EN"]["rich_text"][0]["text"]["content"]) == 2000


def test_empty_en_draft_omits_property(monkeypatch):
    props = _run(monkeypatch, linkedin_draft="DE text", en_draft="")
    assert "LinkedIn Draft EN" not in props


def test_rebuild_body_writes_template_order(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1", "results": [], "has_more": False}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", en_draft="EN",
            image_prompt="PROMPT", image_url="http://img",
            infographic_skeleton="SKEL",
            post_text="ORIG", post_url="http://post",
        )
    children_calls = [c for c in m.call_args_list
                      if "children" in (c.kwargs.get("json") or {})]
    assert len(children_calls) == 1
    children = children_calls[0].kwargs["json"]["children"]
    headings = [b["heading_2"]["rich_text"][0]["text"]["content"]
                for b in children if b["type"] == "heading_2"]
    assert headings == [
        "Generated Image",
        "LinkedIn Draft DE (Slot: Vormittag)",
        "LinkedIn Draft EN (Slot: Nachmittag)",
        "Original Post",
        "Post Text (Original)",
        "Infografik-Skelett (Canva)",
        "Image Prompt",
    ]
