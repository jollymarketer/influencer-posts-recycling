"""Matrix/persona/asset Notion plumbing. HTTP mocked via _notion_request."""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db


def _query_response(pages):
    resp = MagicMock()
    resp.json.return_value = {"results": pages}
    resp.raise_for_status.return_value = None
    return resp


def _page(job=None, stage=None, persona=None, asset=None):
    props = {}
    if job:
        props["Matrix-Job"] = {"select": {"name": job}}
    if stage:
        props["Matrix-Stage"] = {"select": {"name": stage}}
    if persona:
        props["Persona"] = {"select": {"name": persona}}
    if asset:
        props["Asset"] = {"select": {"name": asset}}
    return {"properties": props}


def test_get_recent_boxes_pairs_job_and_stage():
    pages = [_page("Perspective", "Awareness"), _page("Proof", "Selection"),
             _page(job="Perspective")]  # incomplete row is skipped
    with patch.object(notion_db, "_notion_request", return_value=_query_response(pages)):
        boxes = notion_db.get_recent_boxes()
    assert boxes == [("Perspective", "Awareness"), ("Proof", "Selection")]


def test_get_recent_boxes_widens_window_and_cuts_after_filtering():
    # 3 pages without matrix properties followed by 2 classified pages must
    # not shrink the window: both classified tuples still come back, and the
    # outgoing query must request the wider page_size (50), not limit.
    pages = [_page(), _page(), _page(),
             _page("Perspective", "Awareness"), _page("Proof", "Selection")]
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs.get("json", {}))
        return _query_response(pages)

    with patch.object(notion_db, "_notion_request", side_effect=fake_request):
        boxes = notion_db.get_recent_boxes()
    assert boxes == [("Perspective", "Awareness"), ("Proof", "Selection")]
    assert calls[0]["page_size"] == 50


def test_get_recent_assets_and_personas():
    pages = [_page(asset="case-a", persona="founder-ceo"), _page(asset="case-b")]
    with patch.object(notion_db, "_notion_request", return_value=_query_response(pages)):
        assert notion_db.get_recent_assets() == ["case-a", "case-b"]
        assert notion_db.get_recent_personas() == ["founder-ceo"]


def test_update_with_draft_writes_matrix_properties_nonfatal(monkeypatch):
    monkeypatch.setenv("NOTION_TOKEN", "tok")
    monkeypatch.setattr(notion_db, "MAKE_REVIEW_WEBHOOK", "", raising=False)
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs.get("json", {}))
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"id": "p1"}
        return resp

    with patch.object(notion_db, "_notion_request", side_effect=fake_request):
        notion_db.update_with_draft(
            page_id="p1", linkedin_draft="text", image_prompt="", image_url="",
            matrix_job="Proof", matrix_stage="Selection",
            persona="founder-ceo", asset_id="case-a",
        )
    prop_patches = [c.get("properties", {}) for c in calls]
    flat = {k: v for props in prop_patches for k, v in props.items()}
    assert flat["Matrix-Job"]["select"]["name"] == "Proof"
    assert flat["Matrix-Stage"]["select"]["name"] == "Selection"
    assert flat["Persona"]["select"]["name"] == "founder-ceo"
    assert flat["Asset"]["select"]["name"] == "case-a"
