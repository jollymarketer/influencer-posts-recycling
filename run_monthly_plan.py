"""Monatsplan-CLI: baut den Monatsraster-Vorschlag aus der Themen-DB.

    CLIENT=swot python run_monthly_plan.py --month 2026-10            # Trockenlauf
    CLIENT=swot python run_monthly_plan.py --month 2026-10 --write    # schreibt Themenvorschlaege

Default ist der Trockenlauf. --write schreibt ausschliesslich Status
"Themenvorschlag" in den Redaktionsplan; die Freigabe bleibt ein Handschritt.
"""
import argparse
import sys
from datetime import date

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.monthly_plan import (AXIS_LABEL, active_fristen, build_slots,
                                classify_axes, persist_axes, read_topics,
                                select, write_proposals)

_cfg = load_client()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True, help="Zielmonat, z.B. 2026-10")
    ap.add_argument("--write", action="store_true",
                    help="Vorschlaege in den Redaktionsplan schreiben (Default: Trockenlauf)")
    args = ap.parse_args()
    year, month = (int(x) for x in args.month.split("-"))

    if not hasattr(_cfg, "POSTING_SCHEDULE"):
        raise SystemExit(f"Mandant '{_cfg.NAME}' hat keinen POSTING_SCHEDULE.")

    slots = build_slots(year, month)
    print(f"Slots im {args.month}: {len(slots)}")

    topics = read_topics()
    print(f"Themen mit Status New/Hub needed: {len(topics)}")
    topics = classify_axes(topics)
    n_ax = persist_axes(topics)
    print(f"Achse klassifiziert und in die Themen-DB geschrieben: {n_ax}")

    fristen = active_fristen(date.today(), _cfg.AXIS_MIX["fristen_horizon_days"])
    print(f"aktive Fristen: {[f['id'] for f in fristen]}")

    slots = select(slots, topics, fristen, _cfg.AXIS_MIX, _cfg.AXIS_TO_ACCOUNT)

    filled = [s for s in slots if s.topic or s.frist]
    print(f"\ngefuellt: {len(filled)} von {len(slots)}\n")
    per_axis: dict = {}
    for s in slots:
        mark = ""
        if s.frist:
            text = s.frist["label"]
            mark = "FRIST"
        elif s.topic:
            text = s.topic["title_de"] or s.topic["title"]
        else:
            text = "(leer)"
        if s.axis:
            per_axis[s.axis] = per_axis.get(s.axis, 0) + 1
        print(f"{s.day}  {s.kanal:<28} {(s.axis or '-'):<18} {mark:<5} {text[:70]}")
    print("\nAchsen-Verteilung:", {AXIS_LABEL.get(k, k): v for k, v in per_axis.items()})

    if args.write:
        n = write_proposals(slots)
        print(f"\nals Themenvorschlag in den Redaktionsplan geschrieben: {n}")
    else:
        print("\nTrockenlauf. Schreiben mit --write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
