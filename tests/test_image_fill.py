"""Tests fuer die Kandidaten-Auswahl des Bilder-Laufs (run_image_fill).
Kein Notion-, kein kie.ai-Aufruf.

CLIENT=swot VOR dem Import, gleiche Konvention wie test_monthly_plan: die
Import-Kette (run_plan_fill -> tools.monthly_plan) backt die Config des
Prozess-Mandanten ein; ein jolly-Import hier wuerde die spaeter geladenen
Plan-Tests vergiften."""
import os
import sys

os.environ["CLIENT"] = "swot"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients import load_client

load_client.cache_clear()

import run_image_fill


def _row(pid, status="Text freigegeben", kanal="LinkedIn Robert",
         text="Beitrag", bild=None):
    return {"id": pid, "properties": {
        "Titel": {"title": [{"plain_text": f"Titel {pid}"}]},
        "Status": {"select": {"name": status} if status else None},
        "Kanal": {"select": {"name": kanal} if kanal else None},
        "Post-Text": {"rich_text": [{"plain_text": text}] if text else []},
        "Format": {"select": {"name": "Story"}},
        "Soundbyte": {"rich_text": [{"plain_text": "SB"}]},
        "Infografik-Skelett": {"rich_text": [{"plain_text": "Skelett"}]},
        "Kurzbeschreibung": {"rich_text": [{"plain_text": "Kurz"}]},
        "Bild": {"files": bild or []},
    }}


def test_only_text_freigegeben_linkedin_rows_qualify():
    rows = [
        _row("a"),
        _row("b", status="Entwurf"),
        _row("c", status="Freigegeben"),
        _row("d", kanal="swot.de Blog"),
        _row("e", kanal=None),
        _row("f", text=""),
    ]
    got = run_image_fill.image_candidates(rows)
    assert [k["page_id"] for k in got] == ["a"]
    assert got[0]["format"] == "Story"
    assert got[0]["hat_bild"] is False


def test_existing_image_marks_status_only_candidate():
    rows = [_row("a", bild=[{"name": "post-image.jpg"}])]
    got = run_image_fill.image_candidates(rows)
    assert got[0]["hat_bild"] is True
