"""Einmalig, idempotent: legt das Select "Hook" mit allen Katalog-IDs
(tools/hooks.HOOKS) in der Content-DB des Mandanten an. Mehrfach ausfuehrbar;
fehlende Optionen werden ergaenzt. Aufruf: CLIENT=jolly python scripts/add_hook_property.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.hooks import HOOKS
from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request


def ensure_hook_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    existing = r.json().get("properties", {}).get("Hook")
    have = {o["name"] for o in ((existing or {}).get("select") or {}).get("options", [])}
    missing = [h for h in HOOKS if h not in have]
    if existing and not missing:
        print("Hook-Property vollstaendig - nichts zu tun.")
        return
    options = [{"name": n} for n in sorted(have | set(HOOKS))]
    r = _notion_request("PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(),
                        json={"properties": {"Hook": {"select": {"options": options}}}})
    r.raise_for_status()
    print(f"Hook-Property gesetzt, {len(missing)} Optionen ergaenzt: {', '.join(missing)}")


if __name__ == "__main__":
    ensure_hook_property()
