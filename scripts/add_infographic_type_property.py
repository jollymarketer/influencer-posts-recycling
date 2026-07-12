"""One-time idempotent: adds an 'Infografik-Typ' select property to the
Jolly Influencer Post Recycling Notion DB. Drives the anti-repeat that breaks the
iceberg monotony (get_recent_infographic_types reads this). Safe to run
repeatedly. Notion auto-adds new select options on first write, so the option
list here is just a seed for sensible colors."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

PROP = "Infografik-Typ"
OPTIONS = [
    {"name": "Comparison table", "color": "blue"},
    {"name": "Funnel/pyramid", "color": "green"},
    {"name": "Iceberg", "color": "gray"},
    {"name": "Framework/circles", "color": "purple"},
    {"name": "Horizontal comparison", "color": "yellow"},
    {"name": "Timeline", "color": "orange"},
    {"name": "2x2 matrix", "color": "pink"},
    {"name": "Flywheel/loop", "color": "red"},
    {"name": "Scale/seesaw", "color": "brown"},
    {"name": "Before/after", "color": "default"},
    {"name": "Tree/branching", "color": "green"},
]


def ensure_infographic_type_property() -> None:
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
    ensure_infographic_type_property()
