"""Einmalig: Bild-Properties der Redaktionsplan-KOPIE im SWOT-Workspace auf die
Supabase-URLs umschreiben. Quelle der Zuordnung: $TEMP/swot_image_map.json.

    python scripts/swot_carveout/rewrite_notion_image_urls.py --db <PLAN_COPY_ID>            # Trockenlauf
    python scripts/swot_carveout/rewrite_notion_image_urls.py --db <PLAN_COPY_ID> --write

Schreibt NUR in die angegebene DB und bricht ab, wenn sie die Jolly-Original-ID ist.
Umgeschrieben werden die Property "Bild" und Bild-Bloecke im Seitenkoerper.
"""
import argparse
import json
import os
import sys

import requests
from dotenv import dotenv_values

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
JOLLY_PLAN_DB = "4e7b33b3-e1a3-4e3d-8024-011731d3b373"
MAP_PATH = os.path.join(os.environ.get("TEMP", "."), "swot_image_map.json")
API = "https://api.notion.com/v1"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"}


def rows(token: str, db: str) -> list[dict]:
    out, cur = [], None
    while True:
        body = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        r = requests.post(f"{API}/databases/{db}/query", headers=_h(token), json=body, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j["results"]
        if not j.get("has_more"):
            return out
        cur = j["next_cursor"]


def blocks(token: str, page_id: str) -> list[dict]:
    out, cur = [], None
    while True:
        params = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        r = requests.get(f"{API}/blocks/{page_id}/children", headers=_h(token), params=params, timeout=60)
        r.raise_for_status()
        j = r.json()
        out += j["results"]
        if not j.get("has_more"):
            return out
        cur = j["next_cursor"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    if args.db.replace("-", "") == JOLLY_PLAN_DB.replace("-", ""):
        sys.exit("Das ist die Jolly-Original-DB. Abbruch.")
    token = dotenv_values(os.path.join(ROOT, ".env"))["NOTION_TOKEN_SWOT"]
    with open(MAP_PATH, encoding="utf-8") as fh:
        mapping = json.load(fh)
    props_changed = blocks_changed = unknown = 0
    for page in rows(token, args.db):
        files = (page["properties"].get("Bild") or {}).get("files", [])
        new_files, touched = [], False
        for f in files:
            u = f.get("external", {}).get("url") or f.get("file", {}).get("url", "")
            if u in mapping:
                new_files.append({"name": f.get("name", "post-image.png"), "type": "external",
                                  "external": {"url": mapping[u]}})
                touched = True
            else:
                if "githubusercontent" in u:
                    unknown += 1
                    print(f"  UNBEKANNT (nicht in Map): {u[:100]}")
                new_files.append(f)
        if touched:
            props_changed += 1
            if args.write:
                r = requests.patch(f"{API}/pages/{page['id']}", headers=_h(token),
                                   json={"properties": {"Bild": {"files": new_files}}}, timeout=60)
                r.raise_for_status()
        for b in blocks(token, page["id"]):
            if b.get("type") != "image":
                continue
            u = b["image"].get("external", {}).get("url", "")
            if u in mapping:
                blocks_changed += 1
                if args.write:
                    r = requests.patch(f"{API}/blocks/{b['id']}", headers=_h(token),
                                       json={"image": {"external": {"url": mapping[u]}}}, timeout=60)
                    r.raise_for_status()
    print(f"Seiten mit Bild-Property umgeschrieben: {props_changed}, Bild-Bloecke: {blocks_changed}, unbekannte GitHub-URLs: {unknown}")
    if not args.write:
        print("Trockenlauf. Mit --write schreiben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
