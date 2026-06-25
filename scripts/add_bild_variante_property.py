"""One-time idempotent: adds a 'Bild-Variante' select property to the Influencer
Posts Recycling Notion DB. Stores which image archetype the router chose, which
drives the per-run anti-repeat (get_recent_archetypes reads this) so the daily
image does not lock onto one visual form. Safe to run repeatedly. Notion
auto-adds new select options on first write; the list here is just a seed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

PROP = "Bild-Variante"
OPTIONS = [
    {"name": "editorial_cover", "color": "blue"},
    {"name": "stat_hero", "color": "orange"},
    {"name": "statement_card", "color": "purple"},
    {"name": "two_panel_contrast", "color": "yellow"},
    {"name": "metaphor_object", "color": "green"},
    {"name": "isometric_scene", "color": "pink"},
    {"name": "structured_infographic", "color": "gray"},
]


def ensure_bild_variante_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    if PROP in r.json().get("properties", {}):
        print(f"{PROP} property already exists - nothing to do.")
        return

    payload = {"properties": {PROP: {"select": {"options": OPTIONS}}}}
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(), json=payload
    )
    r.raise_for_status()
    print(f"{PROP} property created with {len(OPTIONS)} seed options.")


if __name__ == "__main__":
    ensure_bild_variante_property()
