"""Bestand des SWOT-Redaktionsplans lesen und bereinigen.

    CLIENT=swot python run_review_backfill.py --report --out <Ordner>

--report liest jede Entwurf-Zeile (Typ LinkedIn-Post, Text vorhanden) mit dem
Leser aus tools/naturalness, schreibt nichts nach Notion und legt Bericht
(.md) und Rohdaten (.json) im Ausgabeordner ab. Kosten: ein Sonnet-Call je
Zeile, bei 50 Zeilen rund 1 EUR.

    CLIENT=swot python run_review_backfill.py --write --out <Ordner> [--refill-passes 3]

--write bereinigt jede Entwurf-Zeile: Leser plus chirurgische Reparatur
(post_scorer._reader_loop), reparierte Texte gehen mit CTA zurueck nach
Notion, Restbefund oder Ueberlaenge leeren den Post-Text. Danach fuellt
run_plan_fill.text_fill die geleerten Zeilen der betroffenen Monate mit dem
neuen Prompt und dem Leser nach, bis zu --refill-passes Durchgaenge (jeder
Durchgang textet nur Zeilen ohne Text). Vor dem ersten Schreiben liegt ein
JSON-Backup aller Post-Texte im Ausgabeordner. "Text freigegeben" und hoeher
wird nie angefasst. Kosten: rund 3 EUR Bereinigung plus 1-2 EUR Nachfuellen.

Siehe tools/review_backfill.py fuer die Regeln und die Spec.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from run_plan_fill import _rt, read_plan, text_fill
from tools import naturalness, review_backfill as rb
from tools.monthly_plan import NOTION_API, TIMEOUT
from tools.post_scorer import client, _reader_loop
from tools.topic_ideas_db import _headers as notion_headers


def read_with_model(text: str, material: str, voice: str):
    try:
        # Structured Output (Sonde 28.08.2026): ohne Schema schrieb das Modell
        # erst eine Prosa-Analyse und lief bei 1024 Tokens ins Limit.
        resp = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4096,
            output_config={"format": {"type": "json_schema", "schema": naturalness.READER_SCHEMA}},
            messages=[{"role": "user", "content": naturalness.reader_prompt(text, material, voice)}],
        )
        return naturalness.parse_findings(resp.content[0].text, text)
    except Exception as e:
        print(f"  Leser fehlgeschlagen: {e}", flush=True)
        return None


def report(out_dir: str, cfg) -> dict:
    rows = rb.plan_rows(read_plan(cfg.CONTENT_PLAN_DB_ID))
    print(f"Entwurf-Zeilen mit Text: {len(rows)}", flush=True)
    results = []
    for i, row in enumerate(rows, 1):
        r = rb.read_row(row, cfg, read_with_model)
        results.append(r)
        print(f"  {i:2d}/{len(rows)} {r['datum']} {r['kanal']:20s} {r['verdikt']:11s} "
              f"{len(r['befunde'])} {r['titel'][:50]}", flush=True)
    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, dt.date.today().isoformat() + "_bestand-report")
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(rb.report_markdown(results))
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(f"Bericht: {stem}.md", flush=True)
    return {"zeilen": len(rows), "befund": sum(1 for r in results if r["verdikt"] == "befund")}


def _backup(rows: list[dict], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, dt.date.today().isoformat() + "_backup-post-texte.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({r["page_id"]: {"titel": r["titel"], "kanal": r["kanal"],
                                  "datum": r["datum"], "text": r["text"]} for r in rows},
                  f, ensure_ascii=False, indent=1)
    return path


def _patch_and_readback(page_id: str, text_neu: str) -> bool:
    """Schreibt und liest zurueck. Weicht die Rueckgelesene vom gewollten
    Text ab (Notion-Eventual-Consistency, kein harter Fehler), ein zweiter
    Versuch; bleibt der Abweicher, False. Ein Notion-Fehler auf dem PATCH
    selbst bricht sofort ab, ohne Neuversuch. Rate-Limit Notion rund 3
    Requests/Sekunde: Pause nach jedem PATCH/GET-Paar."""
    for _ in range(2):
        resp = requests.patch(f"{NOTION_API}/pages/{page_id}", headers=notion_headers(),
                              json={"properties": rb.notion_props_for(text_neu)}, timeout=TIMEOUT)
        if not resp.ok:
            print(f"  Notion-Fehler {resp.status_code}: {resp.text[:160]}", flush=True)
            return False
        back = requests.get(f"{NOTION_API}/pages/{page_id}", headers=notion_headers(), timeout=TIMEOUT)
        back.raise_for_status()
        ist = _rt(back.json()["properties"], "Post-Text")
        ok = ist.strip() == text_neu.strip()
        time.sleep(0.35)
        if ok:
            return True
        print(f"  Readback weicht ab ({len(ist)} statt {len(text_neu)} Zeichen)", flush=True)
    return False


def write(out_dir: str, cfg, refill_passes: int) -> dict:
    """Bereinigt jede Entwurf-Zeile. Ein Notion-Fehler oder eine Ausnahme in
    einer einzelnen Zeile bricht den Lauf nicht ab (Review 28.08.2026): das
    Protokoll wird nach jeder Zeile geschrieben, nicht erst am Ende, sonst
    geht es beim ersten Abbruch verloren. Nachfuellen laeuft nur ueber
    geleert_ids: Zeilen, die dieser Lauf selbst geleert hat, nie ueber
    andere textlose Zeilen im selben Monat (only_page_ids)."""
    rows = rb.plan_rows(read_plan(cfg.CONTENT_PLAN_DB_ID))
    print(f"Entwurf-Zeilen mit Text: {len(rows)}", flush=True)
    print(f"Backup: {_backup(rows, out_dir)}", flush=True)
    zaehler = {"unveraendert": 0, "repariert": 0, "geleert": 0, "fehler": 0}
    monate, protokoll, geleert_ids = set(), [], set()
    stem = os.path.join(out_dir, dt.date.today().isoformat() + "_bestand-write")
    for i, row in enumerate(rows, 1):
        print(f"  {i:2d}/{len(rows)} {row['datum']} {row['kanal']:20s} {row['titel'][:50]}", flush=True)
        try:
            d = rb.decide_row(row, cfg, _reader_loop)
            if d["aktion"] == "unveraendert":
                zaehler["unveraendert"] += 1
            elif _patch_and_readback(d["page_id"], d["text_neu"]):
                zaehler[d["aktion"]] += 1
                if d["aktion"] == "geleert":
                    monate.add(d["datum"][:7])
                    geleert_ids.add(d["page_id"])
                    print(f"    geleert: {d['grund']}", flush=True)
            elif d["aktion"] == "repariert" and _patch_and_readback(d["page_id"], ""):
                d = {**d, "aktion": "geleert", "grund": "Readback-Abweichung, geleert"}
                zaehler["geleert"] += 1
                monate.add(d["datum"][:7])
                geleert_ids.add(d["page_id"])
                print(f"    geleert: {d['grund']}", flush=True)
            else:
                d = {**d, "aktion": "fehler"}
                zaehler["fehler"] += 1
                print(f"    FEHLER {d['page_id']}", flush=True)
            protokoll.append({k: v for k, v in d.items() if k != "text_neu"})
        except Exception as e:
            zaehler["fehler"] += 1
            protokoll.append({"page_id": row["page_id"], "titel": row["titel"], "kanal": row["kanal"],
                              "datum": row["datum"], "aktion": "fehler", "grund": f"Ausnahme: {e}"})
            print(f"    FEHLER {row['page_id']}: {e}", flush=True)
        with open(stem + ".json", "w", encoding="utf-8") as f:
            json.dump({"zaehler": zaehler, "zeilen": protokoll}, f, ensure_ascii=False, indent=1)
    print(f"Bereinigung: {zaehler}, Protokoll {stem}.json", flush=True)
    months = sorted((int(m[:4]), int(m[5:7])) for m in monate)
    for p in range(refill_passes):
        if not months:
            break
        print(f"Nachfuellen, Durchgang {p + 1}: {months}", flush=True)
        r = text_fill(months, cfg=cfg, only_page_ids=geleert_ids)
        print(f"  geschrieben {r['geschrieben']} von {r['zeilen']}", flush=True)
    offen = [r for r in rb.plan_rows_all_entwurf(read_plan(cfg.CONTENT_PLAN_DB_ID)) if not r["text"]]
    print(f"Entwurf-Zeilen ohne Text nach dem Lauf: {len(offen)}", flush=True)
    for r in offen:
        print(f"  OFFEN {r['datum']} {r['kanal']} {r['titel'][:50]}", flush=True)
    for r in protokoll:
        if r["aktion"] == "fehler":
            print(f"  FEHLER {r['datum']} {r['kanal']} {r['titel'][:50]}", flush=True)
    return {**zaehler, "offen": len(offen)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="nur lesen, Bericht schreiben")
    ap.add_argument("--write", action="store_true", help="bereinigen und nachfuellen")
    ap.add_argument("--refill-passes", type=int, default=3)
    ap.add_argument("--out", required=True, help="Ausgabeordner fuer Bericht und Rohdaten")
    args = ap.parse_args()
    if args.report == args.write:
        ap.error("genau eines von --report oder --write angeben")
    cfg = load_client()
    r = report(args.out, cfg) if args.report else write(args.out, cfg, args.refill_passes)
    print(f"Fertig: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
