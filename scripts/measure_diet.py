"""Diaet messen: N Plan-Zeilen trocken texten (ohne Leser-Loop, ohne Notion)
und mit dem Leser aus tools/naturalness lesen. Gleiches Skript vor und nach
der Diaet, Vergleich Befunde je Post.

    CLIENT=swot python scripts/measure_diet.py --n 8 --label alt --out <Ordner>

Kosten: je Post eine Generierung, eine Grammatik, ein Leser, rund 0,10 EUR.
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from unittest.mock import patch

from clients import load_client
from run_plan_fill import read_plan
from run_review_backfill import read_with_model
from tools import post_scorer as ps, post_writer, review_backfill as rb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--label", required=True, help="alt oder neu")
    ap.add_argument("--out", required=True)
    ap.add_argument("--loop", action="store_true",
                    help="Leser-Loop der Pipeline einschalten (Task 5, Trockenlauf mit Log)")
    args = ap.parse_args()
    cfg = load_client()
    rows = rb.plan_rows(read_plan(cfg.CONTENT_PLAN_DB_ID))
    # Abwechselnd beide Konten, feste Reihenfolge nach Termin: gleiche Zeilen
    # in beiden Laeufen.
    rows = sorted(rows, key=lambda r: (r["datum"], r["kanal"]))[: args.n]
    from tools.monthly_plan import axis_id
    from run_plan_fill import _sel
    plan = {r["id"]: r for r in read_plan(cfg.CONTENT_PLAN_DB_ID)}
    prompt_len = len(post_writer.build_prompt("T", "K", rows[0]["kanal"],
                                              cfg.CONTENT_PERSONAS[0]["id"], cfg=cfg,
                                              band="standard", datum="2026-09-10"))
    print(f"DE-Prompt {args.label}: {prompt_len} Zeichen", flush=True)
    results = []
    with patch.dict(ps._cfg.FEATURES, {"naturalness_check": args.loop}):
        for i, row in enumerate(rows, 1):
            achse = axis_id(_sel(plan[row["page_id"]]["properties"], "Achse"))
            r = post_writer.write_post(row["titel"], row["kurz"], row["kanal"], achse,
                                       cfg=cfg, band="standard", datum=row["datum"])
            text = r["text"]
            befunde = rb.read_row({**row, "text": text}, cfg, read_with_model)["befunde"] if text else []
            results.append({"titel": row["titel"], "kanal": row["kanal"], "text": text,
                            "befunde": befunde})
            print(f"  {i}/{len(rows)} {row['kanal']:20s} Befunde {len(befunde)} "
                  f"{'(kein Text)' if not text else ''} {row['titel'][:45]}", flush=True)
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{dt.date.today().isoformat()}_diaet-{args.label}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"prompt_len": prompt_len, "posts": results}, f, ensure_ascii=False, indent=1)
    gesamt = sum(len(r["befunde"]) for r in results)
    mit_text = sum(1 for r in results if r["text"])
    print(f"{args.label}: {mit_text} Texte, {gesamt} Befunde, "
          f"{gesamt / max(mit_text, 1):.2f} je Post, Prompt {prompt_len} Zeichen -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
