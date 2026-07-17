"""Supabase PostgREST wrapper for the topic candidate pool (slate model).

Tables: blog_content_mining.topic_candidates + engine_meta
(scripts/setup_topic_pool_tables.sql). Same raw-requests style as
tools/supabase_db.py: service key, no ORM, custom schema headers.
"""
import os
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

SCHEMA = "blog_content_mining"
TABLE = "topic_candidates"
META_TABLE = "engine_meta"
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


def _headers_patch() -> dict:
    h = _headers_write()
    h["Prefer"] = "return=representation"
    return h


def _url_in(urls: list[str]) -> str:
    quoted = ",".join(f'"{u}"' for u in urls)
    return f"in.({quoted})"


def _check(resp) -> None:
    if not (200 <= resp.status_code < 300):
        raise RuntimeError(f"Supabase {resp.status_code}: {resp.text[:300]}")


def upsert_candidates(rows: list[dict]) -> int:
    """Upsert candidate rows on post_url. Rows use table column names."""
    if not rows:
        return 0
    url = f"{_base_url()}/rest/v1/{TABLE}?on_conflict=post_url"
    resp = requests.post(url, headers=_headers_write(), json=rows, timeout=TIMEOUT)
    _check(resp)
    return len(rows)


def get_pool_urls(client: str) -> set:
    """Every known candidate URL regardless of state (scrape dedup memory)."""
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"select": "post_url", "client": f"eq.{client}"}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    return {r["post_url"] for r in resp.json()}


def get_candidates(client: str, states: list[str]) -> list[dict]:
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {
        "select": "*",
        "client": f"eq.{client}",
        "state": f"in.({','.join(states)})",
    }
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    return resp.json()


def set_state(post_urls: list[str], state: str, extra: dict | None = None) -> None:
    if not post_urls:
        return
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"post_url": _url_in(post_urls)}
    body = {"state": state, **(extra or {})}
    resp = requests.patch(url, headers=_headers_write(), params=params,
                          json=body, timeout=TIMEOUT)
    _check(resp)


def unslate_and_strike(post_urls: list[str], max_times_slated: int) -> None:
    """Slate rows that were NOT picked: +1 strike, back to pool or retired.
    Read-modify-write per row (PostgREST has no atomic increment without RPC;
    a slate is <= 10 rows, so N requests are fine)."""
    if not post_urls:
        return
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {"select": "post_url,times_slated", "post_url": _url_in(post_urls)}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    for row in resp.json():
        count = int(row.get("times_slated", 0)) + 1
        state = "retired" if count >= max_times_slated else "pool"
        presp = requests.patch(
            url, headers=_headers_write(),
            params={"post_url": f'eq.{row["post_url"]}'},
            json={"times_slated": count, "state": state}, timeout=TIMEOUT)
        _check(presp)


def retire_aged(client: str, max_age_days: int) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {
        "client": f"eq.{client}",
        "state": "in.(pool,slated)",
        "first_seen_at": f"lt.{cutoff}",
    }
    resp = requests.patch(url, headers=_headers_patch(), params=params,
                          json={"state": "retired"}, timeout=TIMEOUT)
    _check(resp)
    try:
        return len(resp.json())
    except Exception:
        return 0


def revive_picked(client: str, min_age_days: int) -> int:
    """Winner-Repeat: gepickte Kandidaten nach N Tagen zurueck in den Pool
    (bewaehrte Themen erneut anbieten statt nur Neuware). Frischer Zyklus
    (times_slated=0, first_seen_at=jetzt), damit weder 3-Strikes noch das
    Alters-Retirement den Rueckkehrer sofort wieder entfernen."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=min_age_days)).isoformat()
    url = f"{_base_url()}/rest/v1/{TABLE}"
    params = {
        "client": f"eq.{client}",
        "state": "eq.picked",
        "last_slated_at": f"lt.{cutoff}",
    }
    resp = requests.patch(url, headers=_headers_patch(), params=params,
                          json={"state": "pool", "times_slated": 0,
                                "first_seen_at": now.isoformat()},
                          timeout=TIMEOUT)
    _check(resp)
    try:
        return len(resp.json())
    except Exception:
        return 0


def get_meta(key: str) -> str:
    url = f"{_base_url()}/rest/v1/{META_TABLE}"
    params = {"select": "key,value", "key": f"eq.{key}"}
    resp = requests.get(url, headers=_headers_read(), params=params, timeout=TIMEOUT)
    _check(resp)
    rows = resp.json()
    return rows[0]["value"] if rows else ""


def set_meta(key: str, value: str) -> None:
    url = f"{_base_url()}/rest/v1/{META_TABLE}?on_conflict=key"
    resp = requests.post(url, headers=_headers_write(),
                         json=[{"key": key, "value": value}], timeout=TIMEOUT)
    _check(resp)
