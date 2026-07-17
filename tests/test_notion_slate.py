"""Slate-Notion-Layer: Themenvorschlag-Zeilen, Status-Getter, Archiv."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db

_CAND = {
    "post_url": "https://x.com/p/1",
    "influencer": "Alice",
    "post_text": "Original body text",
    "topic_angle_de": "Warum jede Sprachversion ein zweites Budget frisst",
    "persona": "kaeufer",
    "voc_hit": "versteckte DTP-Kostenlinie",
    "matrix_job": "Perspective",
    "matrix_stage": "Awareness",
    "score_total": 41,
}

_LISOCON_CFG = SimpleNamespace(
    POSTER_BY_PERSONA={"kaeufer": "Reinhard", "anwender": "Jae"},
    POSTER_DEFAULT="Reinhard",
)


def _resp(payload, status=200):
    r = MagicMock(status_code=status)
    r.json.return_value = payload
    r.raise_for_status = MagicMock()
    return r


def test_create_slate_entry_status_and_title(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    monkeypatch.setattr(notion_db, "_cfg", _LISOCON_CFG)
    with patch.object(notion_db, "_notion_request",
                      return_value=_resp({"id": "page-1"})) as req:
        page_id = notion_db.create_slate_entry(_CAND, matrix_prio=True)
    assert page_id == "page-1"
    body = req.call_args.kwargs["json"]
    props = body["properties"]
    assert props["Status"]["select"]["name"] == "Themenvorschlag"
    title = props["title"]["title"][0]["text"]["content"]
    assert title.startswith("Warum jede")
    assert "Alice" not in title  # leak rule
    assert props["Score"]["number"] == 41
    assert props["Matrix-Prio"]["checkbox"] is True
    assert props["Poster"]["select"]["name"] == "Reinhard"  # kaeufer -> Reinhard


def test_create_slate_entry_score_falls_back_to_fresh_score(monkeypatch):
    """Frisch gescorte Kandidaten tragen 'score' statt 'score_total' (Bug 16.07)."""
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    monkeypatch.setattr(notion_db, "_cfg", _LISOCON_CFG)
    cand = {k: v for k, v in _CAND.items() if k != "score_total"}
    cand["score"] = 38
    with patch.object(notion_db, "_notion_request",
                      return_value=_resp({"id": "p"})) as req:
        notion_db.create_slate_entry(cand)
    assert req.call_args.kwargs["json"]["properties"]["Score"]["number"] == 38


def test_create_slate_entry_title_fallback(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    monkeypatch.setattr(notion_db, "_cfg", _LISOCON_CFG)
    cand = {**_CAND, "topic_angle_de": ""}
    with patch.object(notion_db, "_notion_request",
                      return_value=_resp({"id": "p"})) as req:
        notion_db.create_slate_entry(cand)
    title = req.call_args.kwargs["json"]["properties"]["title"]["title"][0]["text"]["content"]
    assert title == "Themenvorschlag"


def test_create_slate_entry_with_draft_writes_props_and_body(monkeypatch):
    """Slate-mit-Draft-Modell (Richard 2026-07-17): Draft entsteht im Slate-Bau,
    Pick = Approved. Draft-Property + Image Prompt + Body via _rebuild_page_body."""
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    monkeypatch.setattr(notion_db, "_cfg", _LISOCON_CFG)
    draft = {"linkedin_draft": "DE Draft Text", "image_prompt": "img prompt",
             "skeleton": "skelett", "post_format": "POV",
             "infographic_type": "Iceberg", "archetype": "stat_hero"}
    with patch.object(notion_db, "_notion_request",
                      return_value=_resp({"id": "page-1"})) as req, \
         patch.object(notion_db, "_rebuild_page_body") as body_mock, \
         patch.object(notion_db, "_patch_select_nonfatal") as sel_mock:
        page_id = notion_db.create_slate_entry(_CAND, matrix_prio=False, draft=draft)
    assert page_id == "page-1"
    props = req.call_args.kwargs["json"]["properties"]
    assert props["Status"]["select"]["name"] == "Themenvorschlag"
    assert props["LinkedIn Draft"]["rich_text"][0]["text"]["content"].startswith("DE Draft")
    assert props["Image Prompt"]["rich_text"][0]["text"]["content"] == "img prompt"
    assert "children" not in req.call_args.kwargs["json"]  # Body kommt aus dem Rebuild
    kwargs = body_mock.call_args.kwargs
    assert kwargs["image_url"] == ""
    assert kwargs["de_draft"] == "DE Draft Text"
    assert kwargs["image_prompt"] == "img prompt"
    assert kwargs["skeleton"] == "skelett"
    patched = {c.args[1]: c.args[2] for c in sel_mock.call_args_list}
    assert patched["Format"] == "POV"
    assert patched["Infografik-Typ"] == "Iceberg"
    assert patched["Bild-Variante"] == "stat_hero"


def test_get_pages_by_status_extracts_fields(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    payload = {"results": [{
        "id": "page-1",
        "properties": {
            "LinkedIn Post URL": {"url": "https://x.com/p/1"},
            "Persona": {"select": {"name": "kaeufer"}},
            "Poster": {"select": {"name": "Reinhard"}},
            "Matrix-Job": {"select": {"name": "Proof"}},
            "Matrix-Stage": {"select": {"name": "Education"}},
        }}], "has_more": False}
    with patch.object(notion_db, "_notion_request", return_value=_resp(payload)) as req:
        rows = notion_db.get_pages_by_status("Topic Approved")
    assert rows == [{"page_id": "page-1", "post_url": "https://x.com/p/1",
                     "persona": "kaeufer", "poster": "Reinhard",
                     "matrix_job": "Proof", "matrix_stage": "Education"}]
    flt = req.call_args.kwargs["json"]["filter"]
    assert flt == {"property": "Status", "select": {"equals": "Topic Approved"}}


def test_get_approved_missing_image_filter(monkeypatch):
    monkeypatch.setattr(notion_db, "NOTION_DB_ID", "db")
    payload = {"results": [], "has_more": False}
    with patch.object(notion_db, "_notion_request", return_value=_resp(payload)) as req:
        notion_db.get_approved_missing_image()
    flt = req.call_args.kwargs["json"]["filter"]
    assert {"property": "Status", "select": {"equals": "Approved"}} in flt["and"]
    assert {"property": "Image", "files": {"is_empty": True}} in flt["and"]


def test_archive_page(monkeypatch):
    with patch.object(notion_db, "_notion_request", return_value=_resp({})) as req:
        notion_db.archive_page("page-1")
    assert req.call_args.args[0] == "PATCH"
    assert req.call_args.kwargs["json"] == {"archived": True}
