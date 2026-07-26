"""Einmaliges Setup der Properties fuer Engagement-Readback und Kommentar-Queue
(Richard 2026-07-26). Idempotent: vorhandene Properties/Optionen bleiben.
Run: CLIENT=lisocon NOTION_DB_ID=<lisocon-db> python scripts/setup_engagement_comment_props.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

NEW_PROPS = {
    "Likes": {"number": {}},
    "Kommentare": {"number": {}},
    "Shares": {"number": {}},
    "Engagement-Stand": {"date": {}},
    "Kommentar-Ziel": {"url": {}},
}
NEW_STATUS_OPTIONS = ["Kommentar"]


def main():
    resp = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}",
                           headers=_headers())
    resp.raise_for_status()
    schema = resp.json()["properties"]

    patch_props = {}
    for name, definition in NEW_PROPS.items():
        if name not in schema:
            patch_props[name] = definition
            print(f"+ Property {name}")

    status_options = schema["Status"]["select"]["options"]
    existing_names = {o["name"] for o in status_options}
    added = [n for n in NEW_STATUS_OPTIONS if n not in existing_names]
    if added:
        # Notion ersetzt die Options-Liste beim PATCH: bestehende Optionen
        # (inkl. IDs/Farben) MUESSEN mitgesendet werden.
        patch_props["Status"] = {"select": {"options": status_options + [
            {"name": n} for n in added]}}
        for n in added:
            print(f"+ Status-Option {n}")

    if not patch_props:
        print("Nichts zu tun - Schema aktuell.")
        return
    resp = _notion_request("PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}",
                           headers=_headers(), json={"properties": patch_props})
    resp.raise_for_status()
    print("Schema aktualisiert.")


if __name__ == "__main__":
    main()
