"""Redaktionsplan fuellen: Termin, Kanal, Bezug und Beitragstext.

    CLIENT=swot python run_plan_fill.py --months 2026-09 2026-10          # Trockenlauf
    CLIENT=swot python run_plan_fill.py --months 2026-09 2026-10 --write  # schreibt

Der Monatsplan (run_monthly_plan.py) legt Themenvorschlaege NEU an. Dieses
Skript arbeitet auf den Zeilen, die schon im Plan stehen: es verteilt sie auf
die Slots der aktiven Konten und schreibt den Text dazu.

Zwei Regeln, beide bewusst:

1. Status geht auf "Entwurf", nie auf "Zur Freigabe". Der Text ist maschinell
   erzeugt und von niemandem gelesen; die kundensichtbare Freigabe-Galerie
   filtert auf "Zur Freigabe", der Flip bleibt ein Handschritt.
2. Ein Text wird nur neu geschrieben, wenn die Zeile das Konto wechselt oder
   noch keinen Text hat. Der Text traegt die Stimme des Kontos, ein Wir-Text
   der Unternehmensseite passt nicht unter Roberts Namen.
"""
import argparse
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.monthly_plan import NOTION_API, TIMEOUT, Topic, build_slots, select
from tools.post_writer import write_post
from tools.topic_ideas_db import _headers as notion_headers

BEZUG = "Basis"


def _title(props, key="Titel") -> str:
    return "".join(x.get("plain_text", "") for x in (props.get(key) or {}).get("title", []))


def _rt(props, key) -> str:
    return "".join(x.get("plain_text", "") for x in (props.get(key) or {}).get("rich_text", []))


def _sel(props, key):
    return ((props.get(key) or {}).get("select") or {}).get("name")


def read_plan(db_id: str) -> list[dict]:
    rows, cur = [], None
    while True:
        payload = {"page_size": 100}
        if cur:
            payload["start_cursor"] = cur
        resp = requests.post(f"{NOTION_API}/databases/{db_id}/query",
                             headers=notion_headers(), json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        j = resp.json()
        rows += j["results"]
        if not j.get("has_more"):
            break
        cur = j["next_cursor"]
    return rows


def plan_topics(rows: list[dict]) -> tuple[list[Topic], dict]:
    """Plan-Zeilen mit Achse als Topic-Objekte, plus Nachschlagewerk je Seite."""
    topics, meta = [], {}
    for r in rows:
        p = r["properties"]
        achse = _sel(p, "Achse")
        if not achse:
            continue
        titel = _title(p)
        topics.append(Topic(page_id=r["id"], title=titel, title_de=titel,
                            keyword_de="", score=0, axis=achse, evidence=""))
        meta[r["id"]] = {
            "titel": titel,
            "achse": achse,
            "kurz": _rt(p, "Kurzbeschreibung"),
            "kanal_alt": _sel(p, "Kanal"),
            "hat_text": bool(_rt(p, "Post-Text")),
        }
    return topics, meta


def fill(months: list[tuple[int, int]], write: bool = False, cfg=None) -> dict:
    cfg = cfg or load_client()
    rows = read_plan(cfg.CONTENT_PLAN_DB_ID)
    topics, meta = plan_topics(rows)
    print(f"Plan-Zeilen mit Achse: {len(topics)}")

    slots = []
    for year, month in months:
        slots += build_slots(year, month)
    print(f"Slots in {len(months)} Monaten, nur aktive Konten: {len(slots)}")

    slots = select(slots, topics, [], cfg.AXIS_MIX, cfg.AXIS_TO_ACCOUNT)
    belegt = [s for s in slots if s.topic]
    print(f"belegt: {len(belegt)} von {len(slots)}")

    gefuellt, neu_geschrieben = 0, 0
    for s in belegt:
        m = meta[s.topic["page_id"]]
        neu_noetig = (not m["hat_text"]) or m["kanal_alt"] != s.kanal
        marke = "NEU" if neu_noetig else "alt"
        print(f"  {s.day} {s.kanal:20s} {marke} {m['titel'][:55]}", flush=True)
        if not write:
            continue
        props = {
            "Geplant für": {"date": {"start": s.day.isoformat()}},
            "Kanal": {"select": {"name": s.kanal}},
            "Bezug": {"select": {"name": BEZUG}},
            "Status": {"select": {"name": "Entwurf"}},
        }
        if neu_noetig:
            text = write_post(m["titel"], m["kurz"], s.kanal, s.axis, cfg=cfg)
            if not text:
                print(f"    kein Text erhalten, Zeile uebersprungen")
                continue
            props["Post-Text"] = {"rich_text": [{"text": {"content": text[:1990]}}]}
            neu_geschrieben += 1
        resp = requests.patch(f"{NOTION_API}/pages/{s.topic['page_id']}",
                              headers=notion_headers(), json={"properties": props},
                              timeout=TIMEOUT)
        if resp.ok:
            gefuellt += 1
        else:
            print(f"    Notion-Fehler {resp.status_code}: {resp.text[:160]}")

    ohne = [t for t in topics if t.page_id not in {s.topic["page_id"] for s in belegt}]
    for t in ohne:
        print(f"  ohne Termin [{t.axis}] {t.title[:70]}")
    return {"belegt": len(belegt), "gefuellt": gefuellt,
            "neu_geschrieben": neu_geschrieben, "ohne_termin": len(ohne)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", nargs="+", required=True,
                    help="Zielmonate, z.B. 2026-09 2026-10")
    ap.add_argument("--write", action="store_true",
                    help="in Notion schreiben (Default: Trockenlauf)")
    args = ap.parse_args()
    months = [tuple(int(x) for x in m.split("-")) for m in args.months]

    r = fill(months, write=args.write)
    print(f"\nbelegt {r['belegt']} | geschrieben {r['gefuellt']} | "
          f"Texte neu {r['neu_geschrieben']} | ohne Termin {r['ohne_termin']}")
    if not args.write:
        print("Trockenlauf, nichts geschrieben. Mit --write ausfuehren.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
