"""Verworfene Redaktionsplan-Zeilen als Lernsignal in die Themen-DB melden.

    CLIENT=swot python run_verworfen_sync.py            # Trockenlauf
    CLIENT=swot python run_verworfen_sync.py --write

Setzt ein Kunde eine Zeile im Redaktionsplan auf "Verworfen", wird das
Ursprungsthema in der Themen-DB auf "Rejected" gestellt. Der taegliche
topic_decisions-Sync (run_research) spiegelt das nach Supabase, und der
Taste-Loop des Minings lernt daraus: der Titel landet als abgelehntes
Beispiel im Few-Shot des naechsten Laufs.

Zuordnung laeuft ueber den Titel (der Redaktionsplan speichert keine
Themen-Page-ID). Umbetitelte Zeilen und Fristen-Slots haben kein
Ursprungsthema; sie werden gemeldet, nie geraten.
"""
import argparse
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from run_plan_fill import _sel, _title, read_plan
from tools.monthly_plan import NOTION_API, TIMEOUT
from tools.topic_decisions_db import _fetch_notion_rows
from tools.topic_ideas_db import _headers


def _norm(s: str) -> str:
    return " ".join((s or "").split()).casefold()


def match_verworfen(plan_titles: list[str], topics: list[dict]) -> tuple[list[dict], list[str]]:
    """Ordnet verworfene Plan-Titel den Themen-DB-Zeilen zu.

    topics: [{"page_id", "title", "title_de", "status"}]. write_proposals
    schreibt titel[:200] aus title_de oder title, deshalb wird auf beide
    Felder und auf den 200-Zeichen-Schnitt verglichen. Rueckgabe:
    (Treffer als Themen-Dicts, Titel ohne Treffer)."""
    index: dict[str, dict] = {}
    for t in topics:
        for key in (t.get("title_de"), t.get("title")):
            if key:
                index.setdefault(_norm(key[:200]), t)
    matches, unmatched = [], []
    seen: set[str] = set()
    for titel in plan_titles:
        t = index.get(_norm(titel))
        if t is None:
            unmatched.append(titel)
        elif t["page_id"] not in seen:
            seen.add(t["page_id"])
            matches.append(t)
    return matches, unmatched


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="Themen-DB-Status auf Rejected setzen (Default: Trockenlauf)")
    args = ap.parse_args()
    cfg = load_client()

    verworfen = []
    for r in read_plan(cfg.CONTENT_PLAN_DB_ID):
        p = r["properties"]
        if _sel(p, "Status") == "Verworfen":
            verworfen.append(_title(p))
    print(f"verworfene Plan-Zeilen: {len(verworfen)}")
    if not verworfen:
        return 0

    topics = []
    for pg in _fetch_notion_rows():
        p = pg["properties"]
        topics.append({
            "page_id": pg["id"],
            "title": "".join(x.get("plain_text", "")
                             for x in (p.get("Title", {}) or {}).get("title", [])),
            "title_de": "".join(x.get("plain_text", "")
                                for x in (p.get("Suggested Title DE", {}) or {}).get("rich_text", [])),
            "status": (((p.get("Status", {}) or {}).get("select")) or {}).get("name", ""),
        })

    matches, unmatched = match_verworfen(verworfen, topics)
    for titel in unmatched:
        print(f"  KEIN THEMA GEFUNDEN (umbetitelt oder Fristen-Slot): {titel[:70]}")

    n = 0
    for t in matches:
        if t["status"] == "Rejected":
            print(f"  schon Rejected: {(t['title_de'] or t['title'])[:70]}")
            continue
        print(f"  -> Rejected: {(t['title_de'] or t['title'])[:70]}")
        if not args.write:
            continue
        resp = requests.patch(
            f"{NOTION_API}/pages/{t['page_id']}", headers=_headers(),
            json={"properties": {"Status": {"select": {"name": "Rejected"}}}},
            timeout=TIMEOUT)
        if resp.ok:
            n += 1
        else:
            print(f"    Notion-Fehler {resp.status_code}: {resp.text[:160]}")
    if args.write:
        print(f"auf Rejected gesetzt: {n}")
    else:
        print("Trockenlauf. Schreiben mit --write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
