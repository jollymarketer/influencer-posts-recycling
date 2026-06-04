"""Tests for Format property read/write. _notion_request mocked."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def test_update_with_draft_writes_format_property(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", image_prompt="", image_url="",
            post_format="Signature",
        )
    # Some _notion_request call must carry the Format select.
    found = None
    for call in m.call_args_list:
        props = call.kwargs.get("json", {}).get("properties", {})
        if "Format" in props:
            found = props["Format"]
    assert found == {"select": {"name": "Signature"}}


def test_update_with_draft_omits_format_when_blank(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"id": "page1"}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp) as m:
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", image_prompt="", image_url="",
        )
    for call in m.call_args_list:
        props = call.kwargs.get("json", {}).get("properties", {})
        assert "Format" not in props


def test_format_write_failure_is_non_fatal(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    ok = MagicMock(status_code=200)
    ok.json.return_value = {"id": "page1"}
    ok.raise_for_status.return_value = None
    bad = MagicMock(status_code=400)
    bad.raise_for_status.side_effect = Exception("no such property Format")

    def route(method, url, **kw):
        # The Format-only PATCH carries exactly {"Format": ...} in properties.
        props = kw.get("json", {}).get("properties", {})
        if list(props.keys()) == ["Format"]:
            return bad
        return ok

    with patch("tools.notion_db._notion_request", side_effect=route):
        # Must not raise despite the Format write failing.
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="DE", image_prompt="", image_url="",
            post_format="POV",
        )


def test_get_recent_formats_parses_selects():
    page = lambda name: {"properties": {"Format": {"select": {"name": name}}}}
    resp = MagicMock()
    resp.json.return_value = {"results": [page("POV"), page("Opinion")]}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp):
        assert notion_db.get_recent_formats(3) == ["POV", "Opinion"]


def test_get_recent_formats_skips_missing_property():
    resp = MagicMock()
    resp.json.return_value = {"results": [{"properties": {}}, {"properties": {"Format": {"select": None}}}]}
    resp.raise_for_status.return_value = None
    with patch("tools.notion_db._notion_request", return_value=resp):
        assert notion_db.get_recent_formats(3) == []
