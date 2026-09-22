"""Einmalig: alle Bild-URLs des Jolly-Redaktionsplans (raw.githubusercontent.com)
herunterladen und in den SWOT-Bucket post-images laden.

    python scripts/swot_carveout/migrate_images.py            # zaehlt, laedt nichts
    python scripts/swot_carveout/migrate_images.py --write    # laedt hoch

Ergebnis: $TEMP/swot_image_map.json  {alte_url: neue_url}. Pfad im Bucket:
migrated-2026-09/<dateiname aus der alten URL>. Idempotent (x-upsert).
"""
import argparse
import json
import os
import sys
from urllib.parse import urlparse

import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SWOT_ENV = "C:/Users/richa/Jolly_Claude_Code/Clients/SWOT/swot-outbound-engine/.env"
PLAN_DB = "4e7b33b3-e1a3-4e3d-8024-011731d3b373"
BUCKET, PREFIX = "post-images", "migrated-2026-09"
MAP_PATH = os.path.join(os.environ.get("TEMP", "."), "swot_image_map.json")


def notion_rows(token: str, db: str) -> list[dict]:
    h = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"}
    rows, cur = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        j = requests.post(f"https://api.notion.com/v1/databases/{db}/query", headers=h, json=body, timeout=60).json()
        rows += j["results"]
        if not j.get("has_more"):
            return rows
        cur = j["next_cursor"]


def image_urls(rows: list[dict]) -> list[str]:
    urls = []
    for r in rows:
        for f in (r["properties"].get("Bild") or {}).get("files", []):
            u = f.get("external", {}).get("url") or f.get("file", {}).get("url", "")
            if u and u not in urls:
                urls.append(u)
    return urls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    jolly_token = dotenv_values(os.path.join(ROOT, ".env"))["NOTION_TOKEN"]
    sw = dotenv_values(SWOT_ENV)
    dst, key = sw["SUPABASE_URL"].rstrip("/"), sw["SUPABASE_SERVICE_ROLE_KEY"]
    urls = image_urls(notion_rows(jolly_token, PLAN_DB))
    gh = [u for u in urls if "githubusercontent" in u]
    print(f"Bild-URLs: {len(urls)}, davon GitHub: {len(gh)}, andere: {len(urls) - len(gh)}")
    for u in urls:
        if u not in gh:
            print("  nicht-GitHub, bleibt:", u[:100])
    names_seen: dict[str, str] = {}
    mapping = {}
    for u in gh:
        name = os.path.basename(urlparse(u).path)
        if name in names_seen and names_seen[name] != u:
            sys.exit(f"Dateinamen-Kollision: {name} kommt von zwei verschiedenen URLs "
                      f"({names_seen[name][:100]} und {u[:100]}). Abbruch.")
        names_seen[name] = u
        new = f"{dst}/storage/v1/object/public/{BUCKET}/{PREFIX}/{name}"
        mapping[u] = new
        if not args.write:
            continue
        img = requests.get(u, timeout=60)
        img.raise_for_status()
        up = requests.post(f"{dst}/storage/v1/object/{BUCKET}/{PREFIX}/{name}",
                           headers={"Authorization": f"Bearer {key}", "apikey": key,
                                    "Content-Type": "image/png", "x-upsert": "true"},
                           data=img.content, timeout=120)
        if not up.ok:
            sys.exit(f"Upload {name}: HTTP {up.status_code} {up.text[:200]}")
        chk = requests.head(new, timeout=30)
        print(f"  {name}: {len(img.content)} B, public HEAD {chk.status_code}")
    with open(MAP_PATH, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, indent=1)
    print(f"Map: {MAP_PATH} ({len(mapping)} Eintraege)")
    if not args.write:
        print("Trockenlauf. Mit --write hochladen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
