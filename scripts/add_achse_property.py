"""One-time idempotent: adds an 'Achse' select property (acht GTM-Themenachsen)
to the Jolly Linkedin Content Creation Notion DB. Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

OPTIONEN = [
    ("outbound_maschine", "blue"),
    ("daten_und_revops", "green"),
    ("positionierung_und_angebot", "orange"),
    ("sales_prozess", "purple"),
    ("team_und_enablement", "yellow"),
    ("inbound_und_content", "pink"),
    ("bestand_und_expansion", "brown"),
    ("ki_im_gtm", "red"),
]


def ensure_achse_property() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    if "Achse" in r.json().get("properties", {}):
        print("Achse property already exists - nothing to do.")
        return

    payload = {"properties": {"Achse": {"select": {
        "options": [{"name": name, "color": color} for name, color in OPTIONEN]}}}}
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(), json=payload
    )
    r.raise_for_status()
    print(f"Achse property created ({len(OPTIONEN)} Achsen).")


if __name__ == "__main__":
    ensure_achse_property()
