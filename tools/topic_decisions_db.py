"""Taste-Loop: mirror Richard's Notion topic decisions into Supabase
(blog_content_mining.topic_decisions) and read the picked/rejected corpus
back as few-shot context for the weekly mining prompt.

One writer path: the daily sync reads ALL Blog-Pipeline rows from Notion and
upserts them — fresh candidates arrive as decision='pending', Richard's status
flips become decision='picked'/'rejected'. The first run doubles as backfill.
"""
import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from tools.supabase_db import _base_url, _key

load_dotenv()

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
TIMEOUT = 30
SCHEMA = "blog_content_mining"
TABLE = "topic_decisions"

# Rows created before this date carry snake_case junk titles (pre title-fix)
# and 39 undocumented bulk-rejects — too noisy as a taste signal.
LEARN_CUTOFF = "2026-07-10"

# Notion Status -> decision. Error counts as picked: the failure happened
# AFTER Richard's Ready-flip, so the taste signal (he chose it) stands.
_PICKED = {"Ready for Generation", "Generating", "Draft", "Review needed", "Published", "Promoted", "Error"}
_REJECTED = {"Rejected"}


def _notion_headers() -> dict:
    tok = os.getenv("NOTION_TOKEN", "")
    if not tok:
        raise RuntimeError("NOTION_TOKEN is not set.")
    return {
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _supabase_headers() -> dict:
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": SCHEMA,
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _rt(props: dict, key: str) -> str:
    return "".join(x.get("plain_text", "") for x in (props.get(key, {}) or {}).get("rich_text", []))


def _sel(props: dict, key: str) -> str:
    return (((props.get(key, {}) or {}).get("select")) or {}).get("name", "")


def _fetch_notion_rows() -> list[dict]:
    db_id = os.getenv("TOPIC_IDEAS_DB_ID", "")
    if not db_id:
        raise RuntimeError("TOPIC_IDEAS_DB_ID is not set.")
    rows: list[dict] = []
    cursor = None
    while True:
        body: dict = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            f"{NOTION_API}/databases/{db_id}/query",
            headers=_notion_headers(), json=body, timeout=TIMEOUT,
        )
        resp.raise_for_status()
        page = resp.json()
        rows.extend(page["results"])
        if not page.get("has_more"):
            break
        cursor = page["next_cursor"]
    return rows


def _to_decision_row(page: dict, now_iso: str) -> dict:
    p = page["properties"]
    status = _sel(p, "Status")
    if status in _PICKED:
        decision = "picked"
    elif status in _REJECTED:
        decision = "rejected"
    else:
        decision = "pending"
    # Only Richard flips to Ready; a reject is his unless the classifier did it.
    if decision == "picked":
        source = "richard"
    elif decision == "rejected":
        source = "auto_classifier" if _sel(p, "Classification") == "Reject" else "richard"
    else:
        source = ""
    created = page.get("created_time", "")
    title_prop = "".join(
        x.get("plain_text", "") for x in (p.get("Title", {}) or {}).get("title", [])
    )
    return {
        "notion_page_id": page["id"],
        "batch_date": created[:10] or None,
        "theme_label": title_prop,
        "title_de": _rt(p, "Suggested Title DE"),
        "title_en": _rt(p, "Suggested Title EN"),
        "keyword_de": _rt(p, "Keyword DE"),
        "keyword_en": _rt(p, "Keyword EN"),
        "blog_score": (p.get("Blog Score", {}) or {}).get("number"),
        "cluster_size": (p.get("Cluster Size", {}) or {}).get("number"),
        "source_influencers": _rt(p, "Source Influencers"),
        "parent_hub_url": (p.get("Parent Hub URL", {}) or {}).get("url") or "",
        "classification": _sel(p, "Classification"),
        "status": status,
        "decision": decision,
        "decision_source": source,
        "decided_at": page.get("last_edited_time") if decision != "pending" else None,
        "learn": created[:10] >= LEARN_CUTOFF,
        "last_synced_at": now_iso,
    }


def sync_topic_decisions() -> int:
    """Upsert every Notion Blog-Pipeline row into topic_decisions. Idempotent."""
    pages = _fetch_notion_rows()
    if not pages:
        return 0
    now_iso = datetime.now(timezone.utc).isoformat()
    rows = [_to_decision_row(pg, now_iso) for pg in pages]
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=notion_page_id"
    resp = requests.post(url, headers=_supabase_headers(), json=rows, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase upsert {resp.status_code}: {resp.text[:300]}")
    return len(rows)


def get_taste_corpus(limit_each: int = 20) -> dict:
    """Recent picked/rejected DE titles for mining few-shot. Auto-classifier
    rejects are excluded — they encode policy, not Richard's taste."""
    key = _key()
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": SCHEMA}

    def q(params: dict) -> list[str]:
        resp = requests.get(
            f"{_base_url()}/rest/v1/{TABLE}",
            headers=headers,
            params={"select": "title_de,title_en",
                    "order": "decided_at.desc.nullslast",
                    "limit": str(limit_each), **params},
            timeout=TIMEOUT,
        )
        if not (200 <= resp.status_code < 300):
            raise RuntimeError(f"Supabase get {resp.status_code}: {resp.text[:300]}")
        return [r["title_de"] or r["title_en"] for r in resp.json()
                if (r["title_de"] or r["title_en"])]

    return {
        "picked": q({"decision": "eq.picked", "learn": "is.true"}),
        "rejected": q({"decision": "eq.rejected", "decision_source": "eq.richard",
                       "learn": "is.true"}),
    }
