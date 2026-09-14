"""Watchlist in Supabase (14.09.2026): Lesen seitenweise, Upsert in Bloecken,
Kommentarpfad liest bei watchlist_source == "db" von dort. requests gemockt."""
import os
import sys
import types
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import tools.abm_comment_drafts as acd
from tools import watchlist_db as wdb


def _resp(payload, status=200):
    r = MagicMock(status_code=status, ok=status < 400)
    r.json.return_value = payload
    r.text = ""
    return r


def test_get_watchlist_pages_until_short_page(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    pages = [_resp([{"linkedin_url": f"u{i}", "prio": 2, "last_name": "N"} for i in range(1000)]),
             _resp([{"linkedin_url": "u1000", "prio": 1, "last_name": "N"}])]
    with patch("tools.watchlist_db.requests.get", side_effect=pages) as g:
        rows = wdb.get_watchlist("jolly")
    assert len(rows) == 1001 and rows[-1]["prio"] == "1"
    ranges = [c.kwargs["headers"]["Range"] for c in g.call_args_list]
    assert ranges == ["0-999", "1000-1999"]
    assert g.call_args_list[0].kwargs["params"]["client"] == "eq.jolly"


def test_upsert_watchlist_chunks_and_skips_blank_urls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "k")
    rows = [{"linkedin_url": f"u{i}", "prio": "2", "first_name": "A", "last_name": "B",
             "company": "C", "title": "CEO"} for i in range(501)] + [{"linkedin_url": ""}]
    with patch("tools.watchlist_db.requests.post", return_value=_resp(None, 201)) as p:
        assert wdb.upsert_watchlist("jolly", rows) == 501
    assert len(p.call_args_list) == 2
    first = p.call_args_list[0].kwargs["json"]
    assert len(first) == 500 and first[0]["client"] == "jolly" and first[0]["prio"] == 2
    assert "on_conflict=client,linkedin_url" in p.call_args_list[0].args[0]


def test_abm_path_reads_db_when_configured():
    cfg = types.SimpleNamespace(NAME="jolly")
    settings = {"watchlist_source": "db", "exclude_companies": ["in2go"]}
    rows = [{"linkedin_url": "u1", "typ": "person", "company": "InTO in2go", "prio": "1"},
            {"linkedin_url": "u2", "typ": "person", "company": "Realcube", "prio": "1"},
            {"linkedin_url": "", "typ": "person", "company": "X", "prio": "1"}]
    with patch.object(acd, "get_watchlist", MagicMock(return_value=rows)) as g:
        out = acd.watchlist_rows(cfg, settings)
    g.assert_called_once_with("jolly")
    assert [r["linkedin_url"] for r in out] == ["u2"]


def test_abm_path_reads_csv_otherwise(tmp_path):
    p = tmp_path / "wl.csv"
    p.write_text("prio,typ,domain,company,persona,first_name,last_name,title,linkedin_url,"
                 "rolle_committee,email_track,letzter_kommentar_am,kommentar_anzahl\n"
                 "1,person,a.com,A,,Ann,A,CEO,https://l/in/a,,,,\n", encoding="utf-8")
    cfg = types.SimpleNamespace(NAME="lisocon")
    with patch.object(acd, "get_watchlist", MagicMock()) as g:
        out = acd.watchlist_rows(cfg, {"watchlist_csv": str(p)})
    g.assert_not_called()
    assert [r["last_name"] for r in out] == ["A"]


def test_jolly_reads_from_db():
    from clients.jolly import config as jolly
    assert jolly.ABM_COMMENT_DRAFTS["watchlist_source"] == "db"
