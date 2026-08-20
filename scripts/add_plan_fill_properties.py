"""One-time idempotent: legt die drei Maschinerie-Properties im
Content-Redaktionsplan an (CONTENT_PLAN_DB_ID der Client-Config), die
run_plan_fill.py seit 20.08.2026 schreibt:

- Format (Select: Opinion/POV/Signature/Story)
- Soundbyte (Rich Text)
- Infografik-Skelett (Rich Text)

Der Redaktionsplan ist kundensichtbar: die drei Spalten nach dem Anlegen in
den Kunden-Views ausblenden (geht nicht per API). Safe to run repeatedly.

Run: CLIENT=swot python scripts/add_plan_fill_properties.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests

from clients import load_client
from tools.monthly_plan import NOTION_API, TIMEOUT
from tools.post_scorer import VALID_FORMATS
from tools.topic_ideas_db import _headers

_COLORS = ("blue", "green", "orange", "purple")


def ensure_plan_fill_properties() -> None:
    cfg = load_client()
    db_id = cfg.CONTENT_PLAN_DB_ID
    r = requests.get(f"{NOTION_API}/databases/{db_id}", headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    existing = r.json().get("properties", {})

    wanted = {
        "Format": {"select": {"options": [
            {"name": f, "color": c} for f, c in zip(VALID_FORMATS, _COLORS)
        ]}},
        "Soundbyte": {"rich_text": {}},
        "Infografik-Skelett": {"rich_text": {}},
    }
    missing = {k: v for k, v in wanted.items() if k not in existing}
    if not missing:
        print("Alle Plan-Fill-Properties existieren bereits - nichts zu tun.")
        return

    r = requests.patch(f"{NOTION_API}/databases/{db_id}", headers=_headers(),
                       json={"properties": missing}, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"Angelegt: {', '.join(missing)}. In den Kunden-Views ausblenden.")


if __name__ == "__main__":
    ensure_plan_fill_properties()
