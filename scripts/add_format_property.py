"""One-time idempotent: adds a 'Format' select property (Opinion/POV/Signature)
to the Influencer Posts Recycling Notion DB. Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request


def ensure_format_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    if "Format" in r.json().get("properties", {}):
        print("Format property already exists - nothing to do.")
        return

    payload = {
        "properties": {
            "Format": {
                "select": {
                    "options": [
                        {"name": "Opinion", "color": "blue"},
                        {"name": "POV", "color": "green"},
                        {"name": "Signature", "color": "orange"},
                    ]
                }
            }
        }
    }
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(), json=payload
    )
    r.raise_for_status()
    print("Format property created (Opinion / POV / Signature).")


if __name__ == "__main__":
    ensure_format_property()
