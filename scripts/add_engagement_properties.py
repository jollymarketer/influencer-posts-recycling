"""One-time idempotent: adds the four Engagement-Readback properties (Likes,
Kommentare, Shares, Engagement-Stand) to the active client's Notion DB.
Die jolly-DB hatte sie nie, weshalb 85 veroeffentlichte Zeilen ohne Zahlen
dastanden. Run with CLIENT=<name>. Safe to run repeatedly, nur additiv."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

WANTED = {
    "Likes": {"number": {"format": "number"}},
    "Kommentare": {"number": {"format": "number"}},
    "Shares": {"number": {"format": "number"}},
    "Engagement-Stand": {"date": {}},
}


def ensure_engagement_properties() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    existing = r.json().get("properties", {})
    missing = {name: spec for name, spec in WANTED.items() if name not in existing}
    if not missing:
        print("Alle vier Engagement-Properties existieren bereits - nichts zu tun.")
        return

    r = _notion_request("PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}",
                        headers=_headers(), json={"properties": missing})
    r.raise_for_status()
    print(f"Angelegt in DB {NOTION_DB_ID}: {', '.join(sorted(missing))}.")


if __name__ == "__main__":
    ensure_engagement_properties()
