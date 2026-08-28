"""Bestand des SWOT-Redaktionsplans lesen und bereinigen.

    CLIENT=swot python run_review_backfill.py --report --out <Ordner>

--report liest jede Entwurf-Zeile (Typ LinkedIn-Post, Text vorhanden) mit dem
Leser aus tools/naturalness, schreibt nichts nach Notion und legt Bericht
(.md) und Rohdaten (.json) im Ausgabeordner ab. Kosten: ein Sonnet-Call je
Zeile, bei 50 Zeilen rund 1 EUR.

Siehe tools/review_backfill.py fuer die Regeln und die Spec.
"""
import argparse
import datetime as dt
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from run_plan_fill import read_plan
from tools import naturalness, review_backfill as rb
from tools.post_scorer import client


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true", help="nur lesen, Bericht schreiben")
    ap.add_argument("--out", required=True, help="Ausgabeordner fuer Bericht und Rohdaten")
    args = ap.parse_args()
    if not args.report:
        ap.error("--report angeben (Schreibmodus folgt in Task 6)")
    cfg = load_client()
    r = report(args.out, cfg)
    print(f"Fertig: {r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
