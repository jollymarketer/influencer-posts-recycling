"""Einmalig: swot-Zeilen aus dem Jolly-Supabase in das SWOT-Projekt kopieren.

    python scripts/swot_carveout/copy_supabase_rows.py            # Trockenlauf, zaehlt nur
    python scripts/swot_carveout/copy_supabase_rows.py --write    # kopiert per Upsert

Quelle: SUPABASE_URL / SUPABASE_SERVICE_KEY aus der Content-Engine-.env.
Ziel:   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY aus der Outbound-Engine-.env von SWOT.
Idempotent (Upsert auf den Primaerschluessel). Schreibt nie in die Quelle.
"""
import argparse
import os
import sys

import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SWOT_ENV = "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env"
SCHEMA = "blog_content_mining"
TABLES = {  # tabelle: (filter-params, on_conflict)
    "influencer_posts": ({"client": "eq.swot"}, "client,post_url"),
    "topic_candidates": ({"client": "eq.swot"}, "post_url"),
    "topic_decisions": ({"client": "eq.swot"}, "notion_page_id"),
    "comment_watchlist": ({"client": "eq.swot"}, "client,linkedin_url"),
    "engine_meta": ({"key": "like.*swot*"}, "key"),
}


def _conn(path: str, key_name: str) -> tuple[str, str]:
    env = dotenv_values(path)
    url, key = (env.get("SUPABASE_URL") or "").rstrip("/"), env.get(key_name) or ""
    if not url or not key:
        sys.exit(f"{path}: SUPABASE_URL oder {key_name} fehlt")
    return url, key


def _headers(key: str, write: bool = False) -> dict:
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    if write:
        h.update({"Content-Profile": SCHEMA, "Content-Type": "application/json",
                  "Prefer": "resolution=merge-duplicates,return=minimal"})
    else:
        h["Accept-Profile"] = SCHEMA
    return h


def fetch_all(url: str, key: str, table: str, params: dict) -> list[dict]:
    rows, offset = [], 0
    while True:
        r = requests.get(f"{url}/rest/v1/{table}", headers=_headers(key),
                         params={**params, "select": "*", "limit": 1000, "offset": offset}, timeout=60)
        r.raise_for_status()
        batch = r.json()
        rows += batch
        if len(batch) < 1000:
            return rows
        offset += 1000


def count(url: str, key: str, table: str, params: dict) -> int:
    r = requests.get(f"{url}/rest/v1/{table}", headers={**_headers(key), "Prefer": "count=exact", "Range": "0-0"},
                     params={**params, "select": "*"}, timeout=60)
    r.raise_for_status()
    return int(r.headers["content-range"].split("/")[1])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    src_url, src_key = _conn(os.path.join(ROOT, ".env"), "SUPABASE_SERVICE_KEY")
    dst_url, dst_key = _conn(SWOT_ENV, "SUPABASE_SERVICE_ROLE_KEY")
    if src_url == dst_url:
        sys.exit("Quelle und Ziel sind dasselbe Projekt. Abbruch.")
    print(f"{'Tabelle':20s} {'Quelle':>7s} {'Ziel vorher':>12s} {'Ziel nachher':>13s}")
    for table, (params, on_conflict) in TABLES.items():
        src_n = count(src_url, src_key, table, params)
        before = count(dst_url, dst_key, table, params)
        after = before
        if args.write and src_n:
            rows = fetch_all(src_url, src_key, table, params)
            for i in range(0, len(rows), 500):
                r = requests.post(f"{dst_url}/rest/v1/{table}", headers=_headers(dst_key, write=True),
                                  params={"on_conflict": on_conflict}, json=rows[i:i + 500], timeout=120)
                if not r.ok:
                    sys.exit(f"{table}: HTTP {r.status_code} {r.text[:300]}")
            after = count(dst_url, dst_key, table, params)
        print(f"{table:20s} {src_n:7d} {before:12d} {after:13d}")
    if not args.write:
        print("\nTrockenlauf. Mit --write kopieren.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
