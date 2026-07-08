"""One-time idempotent: adds Matrix-Job / Matrix-Stage / Persona / Asset
select properties to the client's content DB. Persona/Asset options
auto-populate on first write. Run per tenant:
  PYTHONPATH="$(pwd)" python scripts/add_matrix_properties.py            # jolly
  CLIENT=lisocon PYTHONPATH="$(pwd)" python scripts/add_matrix_properties.py
Safe to run repeatedly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.notion_db import NOTION_API, NOTION_DB_ID, _headers, _notion_request

PROPERTIES = {
    "Matrix-Job": [
        {"name": "Perspective", "color": "blue"},
        {"name": "Proof", "color": "green"},
        {"name": "Promotion", "color": "orange"},
    ],
    "Matrix-Stage": [
        {"name": "Awareness", "color": "blue"},
        {"name": "Education", "color": "green"},
        {"name": "Selection", "color": "orange"},
    ],
    "Persona": [],  # options auto-create on first page write
    "Asset": [],    # options auto-create on first page write
}


def ensure_matrix_properties() -> None:
    r = _notion_request("GET", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers())
    r.raise_for_status()
    existing = r.json().get("properties", {})
    to_add = {
        name: {"select": {"options": options}}
        for name, options in PROPERTIES.items()
        if name not in existing
    }
    if not to_add:
        print("All matrix properties already exist - nothing to do.")
        return
    r = _notion_request(
        "PATCH", f"{NOTION_API}/databases/{NOTION_DB_ID}", headers=_headers(),
        json={"properties": to_add},
    )
    r.raise_for_status()
    print(f"Created properties: {', '.join(to_add)}")


if __name__ == "__main__":
    ensure_matrix_properties()
