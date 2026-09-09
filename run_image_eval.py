"""Bild-Varianten zur Bewertung: je Plan-Zeile DREI verschiedene Archetypen.

    CLIENT=swot python run_image_eval.py                     # Trockenlauf
    CLIENT=swot python run_image_eval.py --write --limit 1   # ein Beitrag
    CLIENT=swot python run_image_eval.py --write             # alle

Einmal-Lauf (Richard 09.09.2026) fuer SWOT: der Kunde soll aus drei Bildtypen
je Beitrag waehlen, bevor der Regelpfad (run_image_fill, ein Bild je Zeile
nach "Text freigegeben") laeuft. Deshalb weicht dieser Lauf bewusst ab:

- Quelle sind Zeilen mit Status "Entwurf" (Default, --status ueberschreibt),
  LinkedIn-Kanal, mit Post-Text. Der Status wird NICHT veraendert.
- Je Zeile drei verschiedene Archetypen aus dem Menue in image_archetypes,
  gewaehlt ueber select_archetype mit Anti-Repeat gegen die schon gewaehlten.
- Alle drei Bilder haengen in der Property "Bild" (Dateiname = Archetyp) und
  stehen mit Ueberschrift im Seitenkoerper, damit der Kunde sie gross
  vergleichen kann.
- Zeilen, die schon Dateien in "Bild" tragen, werden uebersprungen (--force
  hebt das auf), damit ein abgebrochener Lauf nicht doppelt generiert.

Kosten ~0,10-0,15 USD je Bild (kie.ai-Konto des Mandanten), dazu je Bild ein
Sonnet-Plan und zwei Vision-Aufrufe. Ergebnisse je Zeile in
.tmp/image_eval_<client>.json, damit ein Abbruch keine URLs verliert.
"""
import argparse
import json
import os
import sys
from datetime import date

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from run_plan_fill import _rt, _sel, _title, read_plan
from tools.image_archetypes import (
    ARCHETYPES,
    build_archetype_prompt,
    plan_visual,
    select_archetype,
    skeleton_signals,
)
from tools.kieai_image import generate_image
from tools.monthly_plan import NOTION_API, TIMEOUT
from tools.post_scorer import normalize_infographic_type, parse_infographic_type
from tools.topic_ideas_db import _headers as notion_headers

VARIANTS_PER_POST = 3


def eval_candidates(rows: list[dict], status: str = "Entwurf",
                    force: bool = False) -> list[dict]:
    """Zeilen fuer den Bewertungslauf: gewuenschter Status, LinkedIn-Kanal,
    Post-Text vorhanden. Ohne --force fallen Zeilen mit Bild heraus."""
    out = []
    for r in rows:
        p = r["properties"]
        if _sel(p, "Status") != status:
            continue
        kanal = _sel(p, "Kanal") or ""
        if not kanal.startswith("LinkedIn"):
            continue
        if not _rt(p, "Post-Text"):
            continue
        hat_bild = bool((p.get("Bild") or {}).get("files"))
        if hat_bild and not force:
            continue
        out.append({
            "page_id": r["id"],
            "titel": _title(p),
            "kanal": kanal,
            "format": _sel(p, "Format") or "Opinion",
            "soundbyte": _rt(p, "Soundbyte"),
            "skeleton": _rt(p, "Infografik-Skelett"),
            "kurz": _rt(p, "Kurzbeschreibung"),
            "hat_bild": hat_bild,
        })
    return out


def pick_variants(k: dict, n: int = VARIANTS_PER_POST) -> list[str]:
    """n verschiedene Archetypen fuer eine Zeile, in Praeferenz-Reihenfolge des
    Selektors. Der Anti-Repeat des Selektors meidet nur die letzten zwei, ab
    dem vierten Wunsch wuerde er wiederholen; n bleibt deshalb bei 3."""
    ityp = normalize_infographic_type(parse_infographic_type(k["skeleton"]))
    sig = skeleton_signals(k["skeleton"], k["soundbyte"])
    chosen: list[str] = []
    while len(chosen) < n:
        a = select_archetype(k["format"], ityp, recent_archetypes=list(chosen), **sig)
        if a in chosen:
            break
        chosen.append(a)
    return chosen


def _write_variants(page_id: str, variants: list[dict]) -> None:
    """Alle Varianten in die Property "Bild" und als Bloecke in den Koerper.
    Status bleibt unberuehrt."""
    files = [{"name": f"{v['label']}.png", "type": "external",
              "external": {"url": v["url"]}} for v in variants]
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}", headers=notion_headers(), timeout=TIMEOUT,
        json={"properties": {"Bild": {"files": files}}})
    resp.raise_for_status()

    children = [{"object": "block", "type": "heading_2", "heading_2": {
        "rich_text": [{"type": "text", "text": {
            "content": f"Bildvarianten zur Auswahl ({date.today():%d.%m.%Y})"}}]}}]
    for i, v in enumerate(variants, 1):
        children.append({"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"type": "text", "text": {
                "content": f"Variante {i}: {v['label']}"},
                "annotations": {"bold": True}}]}})
        children.append({"object": "block", "type": "image", "image": {
            "type": "external", "external": {"url": v["url"]}}})
    resp = requests.patch(
        f"{NOTION_API}/blocks/{page_id}/children", headers=notion_headers(),
        timeout=TIMEOUT, json={"children": children})
    resp.raise_for_status()


def run(write: bool = False, limit: int = 0, status: str = "Entwurf",
        force: bool = False, cfg=None) -> dict:
    cfg = cfg or load_client()
    rows = read_plan(cfg.CONTENT_PLAN_DB_ID)
    kandidaten = eval_candidates(rows, status=status, force=force)
    print(f"Zeilen mit Status '{status}' ohne Bild: {len(kandidaten)}")

    language = getattr(cfg, "IMAGE_LANGUAGE", "German")
    os.makedirs(".tmp", exist_ok=True)
    log_path = f".tmp/image_eval_{cfg.NAME}.json"
    log = json.load(open(log_path, encoding="utf-8")) if os.path.exists(log_path) else {}

    posts, bilder, fehler = 0, 0, 0
    for k in kandidaten:
        if limit and posts >= limit:
            print(f"  Deckel --limit {limit} erreicht.")
            break
        archetypes = pick_variants(k)
        print(f"\n{k['kanal']:22s} {k['titel'][:60]}")
        print(f"  Varianten: {', '.join(ARCHETYPES[a]['label'] for a in archetypes)}")
        if not write:
            posts += 1
            continue
        variants = []
        for a in archetypes:
            visual = plan_visual(a, soundbyte=k["soundbyte"], kontext=k["kurz"],
                                 skeleton=k["skeleton"], language=language)
            eff, prompt, ratio, strip = build_archetype_prompt(
                a, soundbyte=k["soundbyte"], kontext=k["kurz"],
                skeleton=k["skeleton"], language=language, visual=visual)
            label = ARCHETYPES[eff]["label"]
            print(f"  -> {label} (angefragt {a})", flush=True)
            try:
                url = generate_image(prompt, aspect_ratio=ratio, strip_marks=strip)
            except Exception as e:
                print(f"    FEHLER, Variante entfaellt: {e}", file=sys.stderr, flush=True)
                fehler += 1
                continue
            variants.append({"archetype": eff, "label": label, "url": url,
                             "headline": (visual or {}).get("headline", "")})
            bilder += 1
            print(f"    OK -> {url}", flush=True)
        log[k["page_id"]] = {"titel": k["titel"], "variants": variants}
        json.dump(log, open(log_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if variants:
            _write_variants(k["page_id"], variants)
            print(f"  Notion: {len(variants)} Variante(n) geschrieben", flush=True)
        posts += 1
    return {"kandidaten": len(kandidaten), "posts": posts, "bilder": bilder,
            "fehler": fehler}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="Bilder generieren und schreiben (Default: Trockenlauf)")
    ap.add_argument("--limit", type=int, default=0,
                    help="hoechstens N Beitraege bearbeiten")
    ap.add_argument("--status", default="Entwurf",
                    help="Quell-Status der Zeilen (Default: Entwurf)")
    ap.add_argument("--force", action="store_true",
                    help="auch Zeilen bearbeiten, die schon ein Bild tragen")
    args = ap.parse_args()

    r = run(write=args.write, limit=args.limit, status=args.status, force=args.force)
    print(f"\nKandidaten {r['kandidaten']} | Beitraege {r['posts']} | "
          f"Bilder {r['bilder']} | Fehler {r['fehler']}")
    if not args.write:
        print("Trockenlauf, nichts generiert. Mit --write ausfuehren.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
