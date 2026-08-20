"""Tests fuer Format-Router, Chunking und neue Properties im Plan-Fill.
Kein Notion-, kein Modellaufruf."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_plan_fill


def _utf16_units(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2


def test_chunks_respect_utf16_limit_and_reassemble():
    text = "ä" * 2500 + "📍" * 1000   # Emoji = 2 UTF-16-Einheiten
    chunks = run_plan_fill._chunks(text)
    assert all(_utf16_units(c) <= 1990 for c in chunks)
    assert "".join(chunks) == text
    assert len(chunks) >= 3


def test_chunks_short_text_single_chunk():
    assert run_plan_fill._chunks("kurz") == ["kurz"]


def _slot(day, kanal, axis, page_id):
    return SimpleNamespace(day=day, kanal=kanal, axis=axis,
                           topic={"page_id": page_id})


def _row(pid, titel="T", achse="fristen"):
    return {"id": pid, "properties": {
        "Titel": {"title": [{"plain_text": titel}]},
        "Achse": {"select": {"name": achse}},
        "Kanal": {"select": None},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": "Herkunft"}]},
        "Post-Text": {"rich_text": []},
    }}


def test_rewrite_flag_forces_new_text_despite_existing():
    from datetime import date
    row = _row("a")
    row["properties"]["Post-Text"] = {"rich_text": [{"plain_text": "alter Text"}]}
    row["properties"]["Kanal"] = {"select": {"name": "LinkedIn Robert"}}
    slots = [_slot(date(2026, 9, 1), "LinkedIn Robert", "fristen", "a")]
    result = {"text": "NEU", "soundbyte": "S", "kontext": "", "skeleton": ""}
    cfg = MagicMock()
    cfg.CONTENT_PLAN_DB_ID = "db"
    resp = MagicMock(ok=True)
    with patch.object(run_plan_fill, "read_plan", return_value=[row]), \
         patch.object(run_plan_fill, "build_slots", return_value=[]), \
         patch.object(run_plan_fill, "select", side_effect=lambda s, *a, **kw: slots), \
         patch.object(run_plan_fill, "pick_format", return_value="Opinion"), \
         patch.object(run_plan_fill, "write_post", return_value=result) as mock_write, \
         patch("run_plan_fill.requests.patch", return_value=resp):
        r = run_plan_fill.fill([(2026, 9)], write=True, cfg=cfg, rewrite=True)
    assert mock_write.called
    assert r["neu_geschrieben"] == 1


def _fill(rows, slots, write_result, fmt="Story"):
    from datetime import date
    cfg = MagicMock()
    cfg.CONTENT_PLAN_DB_ID = "db"
    resp = MagicMock(ok=True)
    with patch.object(run_plan_fill, "read_plan", return_value=rows), \
         patch.object(run_plan_fill, "build_slots", return_value=[]), \
         patch.object(run_plan_fill, "select",
                      side_effect=lambda slots_, *a, **kw: slots), \
         patch.object(run_plan_fill, "pick_format", return_value=fmt) as mock_pick, \
         patch.object(run_plan_fill, "write_post",
                      return_value=write_result) as mock_write, \
         patch("run_plan_fill.requests.patch", return_value=resp) as mock_patch:
        r = run_plan_fill.fill([(2026, 9)], write=True, cfg=cfg)
    return r, mock_pick, mock_write, mock_patch


def test_write_path_sets_format_soundbyte_skeleton_and_chunked_text():
    from datetime import date
    rows = [_row("a")]
    slots = [_slot(date(2026, 9, 1), "LinkedIn Robert", "fristen", "a")]
    result = {"text": "x" * 2500, "soundbyte": "SB", "kontext": "K",
              "skeleton": "TYP: Waage\nEBENEN:\nA: b"}
    r, mock_pick, mock_write, mock_patch = _fill(rows, slots, result)
    props = mock_patch.call_args.kwargs["json"]["properties"]
    assert props["Format"]["select"]["name"] == "Story"
    assert props["Soundbyte"]["rich_text"][0]["text"]["content"] == "SB"
    assert "TYP: Waage" in props["Infografik-Skelett"]["rich_text"][0]["text"]["content"]
    chunks = [t["text"]["content"] for t in props["Post-Text"]["rich_text"]]
    assert "".join(chunks) == "x" * 2500 and len(chunks) == 2
    assert props["Status"]["select"]["name"] == "Entwurf"
    assert r["neu_geschrieben"] == 1


def test_recent_formats_and_types_tracked_per_kanal():
    from datetime import date
    rows = [_row("a"), _row("b"), _row("c")]
    slots = [_slot(date(2026, 9, 1), "LinkedIn Robert", "fristen", "a"),
             _slot(date(2026, 9, 2), "LinkedIn Christian", "fristen", "b"),
             _slot(date(2026, 9, 3), "LinkedIn Robert", "fristen", "c")]
    result = {"text": "T", "soundbyte": "S", "kontext": "",
              "skeleton": "TYP: Eisberg"}
    _, mock_pick, mock_write, _ = _fill(rows, slots, result)
    # Robert-Slot 2 sieht Roberts ersten Format-Pick, nicht Christians.
    recents = [c.args[1] for c in mock_pick.call_args_list]
    assert recents[0] == [] and recents[1] == []
    assert recents[2] == ["Story"]
    # Infografik-Anti-Repeat je Kanal an write_post durchgereicht.
    types_robert = mock_write.call_args_list[2].kwargs["recent_infographic_types"]
    assert types_robert == ["Iceberg"]


def test_dry_run_calls_no_model():
    from datetime import date
    rows = [_row("a")]
    slots = [_slot(date(2026, 9, 1), "LinkedIn Robert", "fristen", "a")]
    cfg = MagicMock()
    cfg.CONTENT_PLAN_DB_ID = "db"
    with patch.object(run_plan_fill, "read_plan", return_value=rows), \
         patch.object(run_plan_fill, "build_slots", return_value=[]), \
         patch.object(run_plan_fill, "select", side_effect=lambda s, *a, **kw: slots), \
         patch.object(run_plan_fill, "pick_format") as mock_pick, \
         patch.object(run_plan_fill, "write_post") as mock_write, \
         patch("run_plan_fill.requests.patch") as mock_patch:
        run_plan_fill.fill([(2026, 9)], write=False, cfg=cfg)
    assert not mock_pick.called and not mock_write.called and not mock_patch.called
