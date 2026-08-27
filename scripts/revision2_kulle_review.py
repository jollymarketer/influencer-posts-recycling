"""Dritte Fassung der 8 von Kulle kommentierten September-Posts.

    CLIENT=swot python .tmp/revision2_kulle_review.py            # Trockenlauf
    CLIENT=swot python .tmp/revision2_kulle_review.py --write    # schreibt

Original bleibt unveraendert. Die Zeile "(Neufassung)" wird auf
"(Revision 1)" umbenannt, darunter entsteht "(Revision 2)" als neue Zeile
mit demselben Termin, Kanal, Achse und derselben Kurzbeschreibung.
Themenplan sortiert nach Geplant fuer, dann Titel: der Basistitel ist
Praefix beider Suffixe, damit steht Original, Revision 1, Revision 2
in dieser Reihenfolge untereinander.

Format wird aus der Zeile uebernommen, nicht neu geroutet: nur die
Stimmprofile haben sich geaendert, der Vergleich soll sonst nichts
verschieben.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.monthly_plan import NOTION_API, TIMEOUT, axis_id
from tools.naturalness import phrases as used_phrases
from tools.post_writer import length_band_for, write_post
from tools.topic_ideas_db import _headers as notion_headers

from run_plan_fill import BEZUG, _date, _rich, _rt, _sel, _title, read_plan

ALT_SUFFIX = " (Neufassung)"
REV1_SUFFIX = " (Revision 1)"
REV2_SUFFIX = " (Revision 2)"


def kandidaten(cfg) -> list[dict]:
    out = []
    for r in read_plan(cfg.CONTENT_PLAN_DB_ID):
        p = r["properties"]
        titel = _title(p)
        if not titel.endswith(ALT_SUFFIX) and not titel.endswith(REV1_SUFFIX):
            continue
        suffix = ALT_SUFFIX if titel.endswith(ALT_SUFFIX) else REV1_SUFFIX
        out.append({
            "page_id": r["id"],
            "basis": titel[: -len(suffix)],
            "suffix": suffix,
            "datum": _date(p),
            "kanal": _sel(p, "Kanal"),
            "achse_label": _sel(p, "Achse"),
            "achse": axis_id(_sel(p, "Achse")),
            "format": _sel(p, "Format") or "Opinion",
            "kurz": _rt(p, "Kurzbeschreibung"),
        })
    out.sort(key=lambda k: (k["datum"], k["basis"]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    cfg = load_client()
    ks = kandidaten(cfg)
    print(f"Kommentierte Neufassungen gefunden: {len(ks)}")
    for k in ks:
        print(f"  {k['datum']} {k['kanal']:20s} {k['format']:10s} {k['basis'][:60]}")
    if not args.write:
        print("\nTrockenlauf, nichts geschrieben.")
        return 0

    bestand = {r["id"] for r in read_plan(cfg.CONTENT_PLAN_DB_ID)}
    fmts_seen: dict[str, list] = {}
    used: dict[str, list] = {}
    neu = 0
    for k in ks:
        seen = fmts_seen.setdefault(k["kanal"], [])
        band = length_band_for(cfg, len(seen))
        r = write_post(k["basis"], k["kurz"], k["kanal"], k["achse"],
                       post_format=k["format"], cfg=cfg, band=band,
                       avoid_phrases=list(used.get(k["kanal"], [])),
                       datum=k["datum"])
        if not r["text"]:
            print(f"  {k['datum']} kein Text erhalten, Zeile uebersprungen")
            continue
        used.setdefault(k["kanal"], []).extend(used_phrases(r["text"]))
        seen.insert(0, k["format"])

        props = {
            "Titel": {"title": [{"text": {"content": k["basis"] + REV2_SUFFIX}}]},
            "Typ": {"select": {"name": "LinkedIn-Post"}},
            "Status": {"select": {"name": "Entwurf"}},
            "Bezug": {"select": {"name": BEZUG}},
            "Kanal": {"select": {"name": k["kanal"]}},
            "Achse": {"select": {"name": k["achse_label"]}},
            "Format": {"select": {"name": k["format"]}},
            "Geplant für": {"date": {"start": k["datum"]}},
            "Kurzbeschreibung": _rich(k["kurz"]),
            "Post-Text": _rich(r["text"]),
            "Soundbyte": _rich(r["soundbyte"]),
            "Infografik-Skelett": _rich(r["skeleton"]),
        }
        resp = requests.post(
            f"{NOTION_API}/pages", headers=notion_headers(),
            json={"parent": {"database_id": cfg.CONTENT_PLAN_DB_ID}, "properties": props},
            timeout=TIMEOUT)
        if not resp.ok:
            print(f"  {k['datum']} ANLEGEN FEHLGESCHLAGEN {resp.status_code} {resp.text[:200]}")
            continue
        neu += 1
        laenge = len(r["text"])
        print(f"  {k['datum']} {k['kanal']:20s} REV2 {k['format']}/{band or 'format'} "
              f"{laenge} Zeichen  {k['basis'][:50]}", flush=True)

        if k["suffix"] == ALT_SUFFIX:
            ren = requests.patch(
                f"{NOTION_API}/pages/{k['page_id']}", headers=notion_headers(),
                json={"properties": {"Titel": {"title": [
                    {"text": {"content": k["basis"] + REV1_SUFFIX}}]}}},
                timeout=TIMEOUT)
            if not ren.ok:
                print(f"    Umbenennen auf Revision 1 fehlgeschlagen: {ren.status_code}")

    print(f"\nNeue Zeilen: {neu} von {len(ks)}. Bestand vorher: {len(bestand)} Zeilen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
