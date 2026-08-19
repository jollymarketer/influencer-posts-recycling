"""Engagement-Readback fuer jolly (Richard 2026-08-19): der Readback lief nur im
Slate-Modus und las fest verdrahtet die lisocon-Poster-Felder. jolly hatte
85 veroeffentlichte Zeilen ohne eine einzige Engagement-Zahl. Diese Tests
halten die Poster-zu-Property-Map mandantenfaehig und die jolly-Verdrahtung fest."""
import importlib
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools import notion_db

jolly = importlib.import_module("clients.jolly.config")
lisocon = importlib.import_module("clients.lisocon.config")

RICHARD_URL = "https://www.linkedin.com/feed/update/urn:li:share:7495389066000000000"
JOLLY_PROPS = {"Richard": "Richard LinkedIn Posted URL"}
LISOCON_PROPS = {"Reinhard": "Posted URL (Reinhard)", "Jae": "Posted URL (Jae)"}


def _query_response(pages):
    resp = MagicMock()
    resp.json.return_value = {"results": pages}
    resp.raise_for_status.return_value = None
    return resp


def _rows(pages, url_props):
    with patch.object(notion_db, "POSTED_URL_PROPS", url_props), \
         patch.object(notion_db, "_notion_request", return_value=_query_response(pages)):
        return notion_db.get_published_rows()


def test_jolly_single_url_property_resolves_live_url():
    """Ein Poster, ein URL-Feld, keine Poster-Spalte: die Zeile muss trotzdem
    eine live_url tragen, sonst findet match_row() sie nie im Scrape."""
    page = {"id": "p1", "properties": {"Richard LinkedIn Posted URL": {"url": RICHARD_URL}}}
    rows = _rows([page], JOLLY_PROPS)
    assert rows[0]["live_url"] == RICHARD_URL


def test_lisocon_poster_picks_its_own_url():
    page = {"id": "p2", "properties": {
        "Poster": {"select": {"name": "Jae"}},
        "Posted URL (Reinhard)": {"url": "https://x/urn:li:share:1111111111111111"},
        "Posted URL (Jae)": {"url": "https://x/urn:li:share:2222222222222222"}}}
    rows = _rows([page], LISOCON_PROPS)
    assert rows[0]["live_url"].endswith("2222222222222222")
    assert rows[0]["poster"] == "Jae"


def test_missing_poster_falls_back_to_any_filled_url():
    page = {"id": "p3", "properties": {
        "Posted URL (Jae)": {"url": "https://x/urn:li:share:3333333333333333"}}}
    rows = _rows([page], LISOCON_PROPS)
    assert rows[0]["live_url"].endswith("3333333333333333")


def test_unpublished_row_without_url_stays_empty():
    rows = _rows([{"id": "p4", "properties": {}}], JOLLY_PROPS)
    assert rows[0]["live_url"] == ""


def test_jolly_config_carries_the_readback_wiring():
    assert jolly.POSTED_URL_PROPS == JOLLY_PROPS
    assert jolly.ENGAGEMENT_READBACK
    assert [p["url"] for p in jolly.OWN_PROFILES] == [
        "https://www.linkedin.com/in/richardbuettner/"]


def test_lisocon_wiring_unchanged():
    assert lisocon.POSTED_URL_PROPS == LISOCON_PROPS
    assert [p["poster"] for p in lisocon.OWN_PROFILES] == ["Reinhard", "Jae"]
