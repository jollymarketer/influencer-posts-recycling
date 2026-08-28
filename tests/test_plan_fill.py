"""Tests fuer den Redaktionsplan-Fueller. Kein Notion-, kein Modellaufruf."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import run_plan_fill
from tools import post_writer


def _row(pid, titel, achse, kanal=None, text=""):
    props = {
        "Titel": {"title": [{"plain_text": titel}]},
        "Achse": {"select": {"name": achse}} if achse else {"select": None},
        "Kanal": {"select": {"name": kanal}} if kanal else {"select": None},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": "Herkunft"}]},
        "Post-Text": {"rich_text": [{"plain_text": text}] if text else []},
    }
    return {"id": pid, "properties": props}


def test_plan_topics_skips_rows_without_axis():
    rows = [_row("a", "Mit Achse", "fristen"), _row("b", "Ohne Achse", None)]
    topics, meta = run_plan_fill.plan_topics(rows)
    assert [t.page_id for t in topics] == ["a"]
    assert "b" not in meta


def test_plan_topics_marks_existing_text_and_channel():
    rows = [_row("a", "T", "fristen", kanal="LinkedIn Robert", text="fertig")]
    _, meta = run_plan_fill.plan_topics(rows)
    assert meta["a"]["hat_text"] is True
    assert meta["a"]["kanal_alt"] == "LinkedIn Robert"


def test_dry_run_writes_nothing():
    rows = [_row("a", "T", "fristen")]
    cfg = MagicMock()
    cfg.CONTENT_PLAN_DB_ID = "db"
    with patch.object(run_plan_fill, "read_plan", return_value=rows), \
         patch.object(run_plan_fill, "build_slots", return_value=["slot"]), \
         patch.object(run_plan_fill, "select", return_value=[]), \
         patch("run_plan_fill.requests.patch") as mock_patch, \
         patch.object(run_plan_fill, "write_post") as mock_write:
        r = run_plan_fill.fill([(2026, 9)], write=False, cfg=cfg)
    assert mock_patch.called is False
    assert mock_write.called is False
    assert r["ohne_termin"] == 1


def test_axis_to_account_never_yields_inactive_channel():
    """Regressionsschutz: ein pausiertes Konto darf keinen Slot bekommen."""
    os.environ["CLIENT"] = "swot"
    from clients import load_client
    from tools.monthly_plan import build_slots
    cfg = load_client()
    kanaele = {s.kanal for s in build_slots(2026, 9)}
    erlaubt = {cfg.POSTING_SCHEDULE[a]["kanal"] for a in cfg.ACTIVE_ACCOUNTS}
    assert kanaele == erlaubt


def test_build_prompt_refuses_unknown_channel():
    cfg = MagicMock()
    cfg.NAME = "swot"
    cfg.ACCOUNT_VOICES = {"LinkedIn Robert": "Stimme"}
    with pytest.raises(KeyError):
        post_writer.build_prompt("T", "K", "LinkedIn Unbekannt", "fristen", cfg=cfg)


def test_build_prompt_carries_voice_persona_and_bans():
    """Stimme und Persona kommen aus dem cfg-Argument; die Sprach-Verbote sind
    seit 20.08.2026 zur Importzeit in das Template gebacken (Prozess-Mandant,
    CLIENT-Env beim Start). Der Test prueft deshalb die Bans des Template-
    Mandanten, nicht die eines zur Laufzeit gereichten cfg."""
    import importlib
    swot = importlib.import_module("clients.swot.config")
    from tools import post_scorer
    prompt = post_writer.build_prompt("Ein Titel", "Herkunft", "LinkedIn Christian",
                                      "fristen", cfg=swot)
    assert "Christian Kulle" in prompt
    assert "Fristen mit Datum" in prompt
    baked_ban = post_scorer._cfg.TOKENS["LANGUAGE_BANS_DE"].splitlines()[0]
    assert baked_ban in prompt
    assert "Ein Titel" in prompt


def test_text_fill_only_page_ids_limits_run_to_named_pages():
    """Bestandsbereinigung (Task 6 Review): das Nachfuellen darf nur die
    selbst geleerten Seiten neu texten, keine andere textlose Zeile im
    selben Monat."""
    def _row_datiert(pid, titel):
        return {"id": pid, "properties": {
            "Titel": {"title": [{"plain_text": titel}]},
            "Achse": {"select": {"name": "fristen"}},
            "Kanal": {"select": {"name": "LinkedIn Robert"}},
            "Kurzbeschreibung": {"rich_text": [{"plain_text": "Herkunft"}]},
            "Post-Text": {"rich_text": []},
            "Geplant für": {"date": {"start": "2026-09-01"}},
        }}
    rows = [_row_datiert("a", "A"), _row_datiert("b", "B")]
    result = {"text": "NEU", "soundbyte": "S", "kontext": "", "skeleton": ""}
    cfg = MagicMock()
    cfg.CONTENT_PLAN_DB_ID = "db"
    resp = MagicMock(ok=True)
    with patch.object(run_plan_fill, "read_plan", return_value=rows), \
         patch.object(run_plan_fill, "pick_format", return_value="Opinion"), \
         patch.object(run_plan_fill, "write_post", return_value=result) as mock_write, \
         patch("run_plan_fill.requests.patch", return_value=resp):
        r = run_plan_fill.text_fill([(2026, 9)], cfg=cfg, only_page_ids={"a"})
    assert r["zeilen"] == 1
    assert mock_write.call_count == 1
    assert mock_write.call_args.args[0] == "A"
