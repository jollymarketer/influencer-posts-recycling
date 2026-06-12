"""One-off: migrate mined rows from Status=New to Type=Spoke + Status='Freigabe offen'.

Idempotent — only touches rows currently Status=New. Run once after the Phase 1
guardrail ships. Safe to re-run (matches nothing on a second pass).
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
TIMEOUT = 30


def _headers() -> dict:
    tok = os.getenv("NOTION_TOKEN", "")
    if not tok:
        raise RuntimeError("NOTION_TOKEN is not set.")
    return {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def main() -> int:
    db = os.getenv("TOPIC_IDEAS_DB_ID", "")
    if not db:
        raise RuntimeError("TOPIC_IDEAS_DB_ID is not set.")
    h = _headers()
    resp = requests.post(
        f"{NOTION_API}/databases/{db}/query",
        headers=h,
        json={"filter": {"property": "Status", "select": {"equals": "New"}}, "page_size": 100},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    rows = resp.json()["results"]
    print(f"rows with Status=New to migrate: {len(rows)}")
    migrated = 0
    for page in rows:
        u = requests.patch(
            f"{NOTION_API}/pages/{page['id']}",
            headers=h,
            json={"properties": {
                "Type": {"select": {"name": "Spoke"}},
                "Status": {"select": {"name": "Freigabe offen"}},
            }},
            timeout=TIMEOUT,
        )
        if u.ok:
            migrated += 1
        else:
            print(f"  FAIL {page['id']}: {u.status_code} {u.text[:200]}")
    print(f"migrated: {migrated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
