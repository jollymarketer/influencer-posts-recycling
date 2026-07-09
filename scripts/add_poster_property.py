"""One-time idempotent: adds a 'Poster' select property (Reinhard/Jae) to the
Lisocon Content-Engine Notion DB (Persona-Split, GTM-Call Jae 2026-07-09).
Run with CLIENT=lisocon + NOTION_DB_ID env. Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request


def ensure_poster_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    if "Poster" in r.json().get("properties", {}):
        print("Poster property already exists - nothing to do.")
        return

    payload = {
        "properties": {
            "Poster": {
                "select": {
                    "options": [
                        {"name": "Reinhard", "color": "blue"},
                        {"name": "Jae", "color": "green"},
                    ]
                }
            }
        }
    }
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(), json=payload
    )
    r.raise_for_status()
    print("Poster property created (Reinhard / Jae).")


if __name__ == "__main__":
    ensure_poster_property()
