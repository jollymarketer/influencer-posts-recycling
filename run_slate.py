"""
Lisocon Slate-Modus (spec docs/superpowers/specs/2026-07-16-lisocon-topic-slate-pool-design.md).

Drei Phasen pro Cron-Lauf (Mo-Fr 07:00 UTC):
  A (immer):  Status=Approved ohne Bild -> Bild generieren
  B (immer):  Status=Topic Approved -> Draft schreiben -> Ready to Review
  C (Mo+Do):  Scrape -> Pool -> Re-Score -> 10er-Slate nach Notion

Nur aktiv bei FEATURES["slate_mode"] (lisocon). Jolly: run_research.run_daily.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Gleicher Score-Gate wie run_research.MIN_SCORE (dort nicht importierbar
# ohne den kompletten Daily-Import-Block zu ziehen).
MIN_SCORE = 25


def select_slate(scored: list, cfg) -> list:
    """Pure Slate-Auswahl: pro Persona-Seite Top-N ueber MIN_SCORE,
    knappe Seite wird von der anderen aufgefuellt (fill_marker=True)."""
    slate_cfg = cfg.SLATE
    per, size = slate_cfg["per_persona"], slate_cfg["size"]
    eligible = sorted((c for c in scored if c.get("score", 0) >= MIN_SCORE),
                      key=lambda c: c["score"], reverse=True)
    sides = {"kaeufer": [], "anwender": []}
    for cand in eligible:
        side = sides.get(cand.get("persona", ""))
        if side is not None and len(side) < per:
            side.append(cand)
    slate = sides["kaeufer"] + sides["anwender"]
    chosen = {c["post_url"] for c in slate}
    for cand in eligible:
        if len(slate) >= size:
            break
        if cand["post_url"] not in chosen:
            slate.append({**cand, "fill_marker": True})
            chosen.add(cand["post_url"])
    return slate[:size]
