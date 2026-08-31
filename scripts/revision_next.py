"""Naechste Revision fuer jedes Thema des SWOT-Content-Plans.

    CLIENT=swot python scripts/revision_next.py                  # Trockenlauf
    CLIENT=swot python scripts/revision_next.py --write          # schreibt
    CLIENT=swot python scripts/revision_next.py --write --limit 3

Anders als revision2_kulle_review.py wird NICHTS ueberschrieben und NICHTS
umbenannt (Richard 31.08.2026). Bestehende Zeilen bleiben, wie sie sind:
Original, Revision 1, Revision 2 ... Darunter entsteht eine neue Zeile mit
der naechsthoeheren Nummer, gleicher Termin, Kanal, Achse, Format und
Kurzbeschreibung.

Themen ohne Revision bekommen "(Revision 1)", Themen mit Revision 2
bekommen "(Revision 3)". Der Themenplan sortiert nach "Geplant fuer", dann
Titel; der Basistitel ist Praefix aller Suffixe, damit stehen die Fassungen
in Reihenfolge untereinander.

Der Text entsteht ueber write_post, also durch die volle Maschinerie
inklusive Leser-Gate und Reparatur-Loop (post_scorer._reader_loop). Liefert
der Lauf keinen Text (Leser verwirft fail-closed), wird KEINE Zeile
angelegt: eine fehlende Revision ist besser als eine leere.

Schreibt ein Protokoll nach Clients/SWOT/Content/Pruefberichte/ zum
Auflisten der Ergebnisse.
"""
import argparse
import json
import os
import re
import sys
from collections import defaultdict

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

REV_RE = re.compile(r"\s*\(Revision (\d+)\)\s*$")
ALT_RE = re.compile(r"\s*\(Neufassung\)\s*$")


def _split_titel(titel: str) -> tuple[str, int]:
    """Basistitel und Revisionsnummer. Original = 0, "(Neufassung)" zaehlt
    als Revision 1 (so hiess Revision 1 vor dem Umbenennen)."""
    m = REV_RE.search(titel)
    if m:
        return titel[: m.start()].strip(), int(m.group(1))
    m = ALT_RE.search(titel)
    if m:
        return titel[: m.start()].strip(), 1
    return titel.strip(), 0


def kandidaten(cfg) -> list[dict]:
    """Ein Eintrag je Basisthema: die naechste Revisionsnummer und die
    Metadaten der hoechsten vorhandenen Fassung (juengster Redaktionsstand)."""
    rows = read_plan(cfg.CONTENT_PLAN_DB_ID)
    gruppen: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for r in rows:
        basis, nummer = _split_titel(_title(r["properties"]))
        if not basis:
            continue
        gruppen[basis].append((nummer, r))

    out = []
    for basis, eintraege in gruppen.items():
        eintraege.sort(key=lambda t: t[0])
        hoechste, quelle = eintraege[-1]
        p = quelle["properties"]
        out.append({
            "basis": basis,
            "quelle_page_id": quelle["id"],
            "quelle_revision": hoechste,
            "neue_revision": hoechste + 1,
            "bestand": [n for n, _ in eintraege],
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
    ap.add_argument("--write", action="store_true",
                    help="ohne diesen Schalter nur Trockenlauf")
    ap.add_argument("--kanal", default="",
                    help="nur dieses Konto, z.B. 'LinkedIn Robert'")
    ap.add_argument("--ab", type=int, default=0,
                    help="die ersten N Themen ueberspringen (Fortsetzen nach "
                         "Abbruch; die Reihenfolge ist deterministisch)")
    ap.add_argument("--limit", type=int, default=0,
                    help="nur die ersten N Themen (Testcharge)")
    ap.add_argument("--protokoll", default="",
                    help="Pfad der JSON-Ergebnisdatei")
    args = ap.parse_args()

    cfg = load_client()
    ks = kandidaten(cfg)
    if args.kanal:
        ks = [k for k in ks if k["kanal"] == args.kanal]
    if args.ab:
        ks = ks[args.ab:]
    if args.limit:
        ks = ks[: args.limit]

    print(f"Themen gefunden: {len(ks)}")
    for k in ks:
        bestand = ", ".join("Original" if n == 0 else f"R{n}" for n in k["bestand"])
        print(f"  {k['datum']} {k['kanal']:20s} {k['format']:10s} "
              f"[{bestand}] -> Revision {k['neue_revision']}  {k['basis'][:55]}")
    if not args.write:
        print("\nTrockenlauf, nichts geschrieben.")
        return 0

    fmts_seen: dict[str, list] = {}
    used: dict[str, list] = {}
    protokoll = []
    neu = 0
    for i, k in enumerate(ks, 1):
        print(f"\n{i}/{len(ks)} {k['datum']} {k['kanal']} {k['basis'][:55]}", flush=True)
        seen = fmts_seen.setdefault(k["kanal"], [])
        band = length_band_for(cfg, len(seen))
        r = write_post(k["basis"], k["kurz"], k["kanal"], k["achse"],
                       post_format=k["format"], cfg=cfg, band=band,
                       avoid_phrases=list(used.get(k["kanal"], [])),
                       datum=k["datum"])
        if not r["text"]:
            print("  kein Text erhalten (Leser oder Textwache), Zeile nicht angelegt")
            protokoll.append({**{x: k[x] for x in
                                 ("basis", "datum", "kanal", "format",
                                  "neue_revision")},
                              "aktion": "uebersprungen",
                              "grund": "kein Text nach Leser-Gate"})
            continue
        used.setdefault(k["kanal"], []).extend(used_phrases(r["text"]))
        seen.insert(0, k["format"])

        titel = f"{k['basis']} (Revision {k['neue_revision']})"
        props = {
            "Titel": {"title": [{"text": {"content": titel}}]},
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
            json={"parent": {"database_id": cfg.CONTENT_PLAN_DB_ID},
                  "properties": props},
            timeout=TIMEOUT)
        if not resp.ok:
            print(f"  SCHREIBEN FEHLGESCHLAGEN {resp.status_code} {resp.text[:200]}")
            protokoll.append({**{x: k[x] for x in
                                 ("basis", "datum", "kanal", "format",
                                  "neue_revision")},
                              "aktion": "fehler",
                              "grund": f"{resp.status_code} {resp.text[:120]}"})
            continue

        neue_id = resp.json().get("id", "")
        neu += 1
        print(f"  angelegt: Revision {k['neue_revision']}, {k['format']}/"
              f"{band or 'format'}, {len(r['text'])} Zeichen", flush=True)
        protokoll.append({**{x: k[x] for x in
                             ("basis", "datum", "kanal", "format",
                              "neue_revision")},
                          "aktion": "angelegt",
                          "grund": "",
                          "page_id": neue_id,
                          "zeichen": len(r["text"]),
                          "band": band or "format",
                          "text": r["text"],
                          "soundbyte": r["soundbyte"]})

    pfad = args.protokoll or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "..", "Clients", "SWOT", "Content", "Pruefberichte",
        "revision_next-protokoll.json")
    pfad = os.path.abspath(pfad)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(protokoll, fh, ensure_ascii=False, indent=1)

    print(f"\nAngelegt: {neu} von {len(ks)} Themen. Protokoll: {pfad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
