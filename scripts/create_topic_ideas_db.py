# scripts/create_topic_ideas_db.py
"""One-time: create the Topic-Ideas Notion DB under a parent page.

Usage:
    python scripts/create_topic_ideas_db.py <parent_page_id>

Prints the new database id. Put it in .env as TOPIC_IDEAS_DB_ID and share the
parent page with the integration first.
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/create_topic_ideas_db.py <parent_page_id>")
        return 1
    parent_page_id = sys.argv[1]
    headers = {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Blog Topic Ideas (mined)"}}],
        "properties": {
            "Title": {"title": {}},
            "Suggested Title EN": {"rich_text": {}},
            "Suggested Title DE": {"rich_text": {}},
            "Keyword EN": {"rich_text": {}},
            "Keyword DE": {"rich_text": {}},
            "Blog Score": {"number": {}},
            "Cluster Size": {"number": {}},
            "Source Influencers": {"rich_text": {}},
            "Supporting Posts": {"rich_text": {}},
            "Status": {"select": {"options": [
                {"name": "New", "color": "blue"},
                {"name": "Promoted", "color": "green"},
                {"name": "Rejected", "color": "red"},
            ]}},
        },
    }
    resp = requests.post(f"{NOTION_API}/databases", headers=headers, json=payload, timeout=30)
    if not resp.ok:
        print(f"Notion error {resp.status_code}: {resp.text[:500]}")
        return 1
    db_id = resp.json()["id"]
    print(f"Created DB. Set in .env:\nTOPIC_IDEAS_DB_ID={db_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
