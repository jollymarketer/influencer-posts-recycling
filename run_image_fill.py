"""Bilder fuer freigegebene Plan-Texte: Status "Text freigegeben" -> "Text+Bild".

    CLIENT=swot python run_image_fill.py                  # Trockenlauf
    CLIENT=swot python run_image_fill.py --write          # generiert + schreibt
    CLIENT=swot python run_image_fill.py --write --limit 1  # Testbild

Prozess-Schritt hinter der Text-Freigabe (Richard 21.08.2026): sobald der
Kunde eine Zeile auf "Text freigegeben" stellt, baut dieser Lauf das Bild
ueber die bestehende Archetyp-Strecke (image_archetypes -> kie.ai -> Brand-
Mark-Wipe -> Logo-Overlay -> GitHub-URL), haengt es an die Property "Bild"
und setzt den Status auf "Text+Bild". Dort prueft der Kunde Text und Bild
zusammen und stellt auf "Freigegeben"; das Posten (Make, noch nicht gebaut)
setzt danach "Gepostet" und fuellt "Geposted am".

Kein Cron: der Lauf startet auf Zuruf. Kosten ~0,10-0,15 USD je Bild
(kie.ai-Konto des Mandanten, bei SWOT KIEAI_API_KEY_SWOT). Traegt eine Zeile
schon ein Bild, wird nur der Status nachgezogen, ohne neue Generierung.

Wie ueberall in der Maschinerie: mit CLIENT=<mandant> starten, die Templates
in image_archetypes sind beim Import mit den TOKENS des Prozess-Mandanten
gefuellt.
"""
import argparse
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from run_plan_fill import _rt, _sel, _title, read_plan
from tools.image_archetypes import (
    build_archetype_prompt,
    select_archetype,
    skeleton_signals,
)
from tools.kieai_image import generate_image
from tools.monthly_plan import NOTION_API, TIMEOUT
from tools.post_scorer import normalize_infographic_type, parse_infographic_type
from tools.topic_ideas_db import _headers as notion_headers

STATUS_QUELLE = "Text freigegeben"
STATUS_ZIEL = "Text+Bild"


def image_candidates(rows: list[dict]) -> list[dict]:
    """Zeilen, die ein Bild brauchen: Status "Text freigegeben", LinkedIn-Kanal,
    mit Post-Text. `hat_bild` markiert Zeilen, die nur den Status-Nachzug
    brauchen (Bild schon da, z.B. nach einem abgebrochenen Lauf)."""
    out = []
    for r in rows:
        p = r["properties"]
        if _sel(p, "Status") != STATUS_QUELLE:
            continue
        kanal = _sel(p, "Kanal") or ""
        if not kanal.startswith("LinkedIn"):
            continue
        if not _rt(p, "Post-Text"):
            continue
        out.append({
            "page_id": r["id"],
            "titel": _title(p),
            "kanal": kanal,
            "format": _sel(p, "Format") or "Opinion",
            "soundbyte": _rt(p, "Soundbyte"),
            "skeleton": _rt(p, "Infografik-Skelett"),
            "kurz": _rt(p, "Kurzbeschreibung"),
            "hat_bild": bool((p.get("Bild") or {}).get("files")),
        })
    return out


def _write_image(page_id: str, image_url: str) -> None:
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}", headers=notion_headers(), timeout=TIMEOUT,
        json={"properties": {
            "Bild": {"files": [{"name": "post-image.jpg", "type": "external",
                                "external": {"url": image_url}}]},
            "Status": {"select": {"name": STATUS_ZIEL}},
        }})
    resp.raise_for_status()
    # Bild zusaetzlich in den Seitenkoerper, damit die Freigabe es gross sieht.
    requests.patch(
        f"{NOTION_API}/blocks/{page_id}/children", headers=notion_headers(),
        timeout=TIMEOUT,
        json={"children": [{"object": "block", "type": "image",
                            "image": {"type": "external",
                                      "external": {"url": image_url}}}]})


def _set_status(page_id: str, status: str) -> None:
    resp = requests.patch(
        f"{NOTION_API}/pages/{page_id}", headers=notion_headers(), timeout=TIMEOUT,
        json={"properties": {"Status": {"select": {"name": status}}}})
    resp.raise_for_status()


def run(write: bool = False, limit: int = 0, cfg=None) -> dict:
    cfg = cfg or load_client()
    rows = read_plan(cfg.CONTENT_PLAN_DB_ID)
    kandidaten = image_candidates(rows)
    print(f"Zeilen mit Status '{STATUS_QUELLE}': {len(kandidaten)}")

    language = getattr(cfg, "IMAGE_LANGUAGE", "German")
    generiert, nachgezogen = 0, 0
    recent_archetypes: dict[str, list] = {}
    for k in kandidaten:
        if limit and generiert >= limit:
            print(f"  Deckel --limit {limit} erreicht.")
            break
        if k["hat_bild"]:
            print(f"  {k['kanal']:22s} Bild da, nur Status: {k['titel'][:50]}")
            if write:
                _set_status(k["page_id"], STATUS_ZIEL)
                nachgezogen += 1
            continue
        recent = recent_archetypes.setdefault(k["kanal"], [])
        ityp = normalize_infographic_type(parse_infographic_type(k["skeleton"]))
        sig = skeleton_signals(k["skeleton"], k["soundbyte"])
        archetype = select_archetype(k["format"], ityp,
                                     recent_archetypes=list(recent), **sig)
        eff, prompt, ratio, strip = build_archetype_prompt(
            archetype, soundbyte=k["soundbyte"], kontext=k["kurz"],
            skeleton=k["skeleton"], language=language)
        print(f"  {k['kanal']:22s} {eff:22s} {k['titel'][:50]}", flush=True)
        recent.insert(0, eff)
        if not write:
            continue
        url = generate_image(prompt, aspect_ratio=ratio, strip_marks=strip)
        _write_image(k["page_id"], url)
        generiert += 1
        print(f"    OK -> {url}", flush=True)
    return {"kandidaten": len(kandidaten), "generiert": generiert,
            "status_nachgezogen": nachgezogen}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="Bilder generieren und schreiben (Default: Trockenlauf)")
    ap.add_argument("--limit", type=int, default=0,
                    help="hoechstens N Bilder generieren (Testlauf)")
    args = ap.parse_args()

    r = run(write=args.write, limit=args.limit)
    print(f"\nKandidaten {r['kandidaten']} | generiert {r['generiert']} | "
          f"Status nachgezogen {r['status_nachgezogen']}")
    if not args.write:
        print("Trockenlauf, nichts generiert. Mit --write ausfuehren.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
