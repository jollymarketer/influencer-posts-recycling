"""Hook-Property lesen und schreiben, weicher System-Check-Befund.
_notion_request gemockt, kein Netz."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db
from tools import system_check as sc


def _resp(payload):
    r = MagicMock(status_code=200)
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def test_update_with_draft_writes_hook_non_fatal(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    with patch("tools.notion_db._notion_request", return_value=_resp({"id": "p1"})) as m:
        notion_db.update_with_draft(page_id="p1", linkedin_draft="DE", image_prompt="",
                                    image_url="", hook="warning")
    found = [c.kwargs.get("json", {}).get("properties", {}).get("Hook")
             for c in m.call_args_list]
    assert {"select": {"name": "warning"}} in found


def test_update_with_draft_survives_missing_hook_property(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)

    def fake(method, url, headers=None, json=None, **kw):
        if json and "Hook" in (json.get("properties") or {}):
            raise RuntimeError("property missing")
        return _resp({"id": "p1"})

    with patch("tools.notion_db._notion_request", side_effect=fake):
        notion_db.update_with_draft(page_id="p1", linkedin_draft="DE", image_prompt="",
                                    image_url="", hook="warning")   # darf nicht werfen


def test_get_recent_hooks_returns_newest_first_and_skips_blank(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    pages = {"results": [
        {"properties": {"Hook": {"select": {"name": "warning"}}}},
        {"properties": {"Hook": {"select": None}}},
        {"properties": {"Hook": {"select": {"name": "cold_open"}}}},
    ]}
    with patch("tools.notion_db._notion_request", return_value=_resp(pages)) as m:
        assert notion_db.get_recent_hooks(limit=20) == ["warning", "cold_open"]
    assert m.call_args.kwargs["json"]["page_size"] == 20


def test_hook_is_an_engagement_dimension():
    assert "Hook" in notion_db.ENGAGEMENT_DIMENSIONS


def test_hook_property_is_soft_and_names_the_seed_script():
    assert "Hook" in sc.SOFT_NOTION_PROPS
    assert "Hook" not in sc.CORE_NOTION_PROPS
    out = sc.soft_notion_findings(present={"Status", "Format"})
    assert len(out) == 1 and out[0]["severity"] == sc.SOFT and not out[0]["ok"]
    assert "scripts/add_hook_property.py" in out[0]["detail"]
    assert sc.soft_notion_findings(present={"Hook"})[0]["ok"]
