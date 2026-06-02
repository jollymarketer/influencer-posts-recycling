"""Supabase PostgREST wrapper for the blog_content_mining schema.

Mirrors the raw-requests style of tools/notion_db.py. Reads SUPABASE_URL and
SUPABASE_SERVICE_KEY from .env. The service-role key bypasses RLS; this is
internal tooling only.
"""
import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "blog_content_mining"
TABLE = "influencer_posts"
TIMEOUT = 30


def _base_url() -> str:
    url = os.environ.get("SUPABASE_URL", "")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set. Add it to .env.")
    return url.rstrip("/")


def _key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_KEY is not set. Add it to .env.")
    return key


def _headers_write() -> dict:
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Content-Profile": SCHEMA,
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _headers_read() -> dict:
    key = _key()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept-Profile": SCHEMA,
    }


def _to_row(post: dict, source: str) -> dict | None:
    url = post.get("post_url")
    if not url:
        return None
    eng = post.get("engagement", {}) or {}
    # Contract: post["date"] is ISO-8601 or absent (scrapers guarantee this).
    date_raw = post.get("date", "")
    post_date = date_raw[:10] if date_raw else None  # ISO -> YYYY-MM-DD
    return {
        "post_url": url,
        "source": source,
        "influencer": post.get("influencer", ""),
        "post_text": post.get("post_text", ""),
        "post_date": post_date,
        "likes": int(eng.get("likes", 0) or 0),
        "comments": int(eng.get("comments", 0) or 0),
        "shares": int(eng.get("shares", 0) or 0),
    }


def upsert_posts(posts: list[dict], source: str) -> int:
    """Upsert posts on conflict post_url. Returns rows sent. Empty list = no-op."""
    rows = [r for r in (_to_row(p, source) for p in posts) if r is not None]
    if not rows:
        return 0
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=post_url"
    resp = requests.post(url, headers=_headers_write(), json=rows, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase upsert {resp.status_code}: {resp.text[:300]}")
    return len(rows)


def get_posts_since(days: int) -> list[dict]:
    """Return all posts with post_date >= now - days."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"select": "*", "post_date": f"gte.{since}"}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase get {resp.status_code}: {resp.text[:300]}")
    return resp.json()
