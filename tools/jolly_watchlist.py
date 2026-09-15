"""Watchlist fuer Jollys Kommentar-Entwuerfe aus drei Quellen bauen
(Richard 14.09.2026, nach zwei Messlaeufen: Themen-Suche liefert Anbieter,
Personen-Listen liefern Kaeufer).

Quellen unter clients/jolly/watchlist/:
- sn_poster_*.jsonl   Sales Navigator Stack 3 "Posted on LinkedIn, 30 Tage", URN je Lead
- hubspot_warm_*.json HubSpot-Kontakte mit warmem Lead-Status und LinkedIn-URL
- pool_active_*.json  Bestandslisten der Outbound-Engine, gesiebt auf Post in 30 Tagen

Prio: 1 HubSpot (warm), 2 SN-Poster (aktiv belegt), 3 Pool-aktiv. Dedupe ueber
den Profil-Schluessel (Vanity oder URN); URN und Vanity derselben Person lassen
sich hier nicht zusammenfuehren, das faengt spaeter der Kommentar-Log per
Post-URL. Ausgabe im Spaltenformat der lisocon-Watchlist. Kein Netz.

Aufruf: python tools/jolly_watchlist.py [--src DIR] [--out CSV] [--push]
Die CSV ist der lokale Bauabzug (gitignored, Repo ist oeffentlich); --push
schreibt die Zeilen nach Supabase, von wo der Kommentarpfad liest.
"""
import argparse
import csv
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SN fuellt hinter den echten Treffern mit Fuzzy-Matches auf (Befund 22.08.2026,
# Stack 1 Slice B); der Titel-Regex nach dem Lauf ist deshalb Pflicht. Gilt nur
# fuer SN-Zeilen: HubSpot-Warmkontakte sind unabhaengig vom Titel warm, die
# Bestandslisten wurden schon beim Listbuild auf den ICP geschnitten.
ICP_TITLE = re.compile(r"gesch[aä]ftsf[uü]hr|gr[uü]nder|founder|\bceo\b|\bcro\b|chief revenue|"
                       r"vp sales|vp of sales|vice president sales|head of sales|vertriebsleit|"
                       r"managing director|inhaber|owner", re.I)

HEADER = ["prio", "typ", "domain", "company", "persona", "first_name", "last_name", "title",
          "linkedin_url", "rolle_committee", "email_track", "letzter_kommentar_am", "kommentar_anzahl"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DEFAULT = os.path.join(ROOT, "clients", "jolly", "watchlist")
OUT_DEFAULT = os.path.join(ROOT, "clients", "jolly", "abm_watchlist.csv")
BLOCK_FILE = "competitor_block.txt"


def _key(url: str) -> str:
    m = re.search(r"linkedin\.com/in/([^/?#]+)", url or "", re.I)
    return m.group(1).lower() if m else ""


def _split_name(name: str) -> tuple[str, str]:
    parts = (name or "").replace("​", "").strip().split()
    if not parts:
        return "", ""
    return " ".join(parts[:-1]), parts[-1]


def _row(prio: str, url: str, name: str, title: str, company: str, source: str = "") -> dict:
    first, last = _split_name(name)
    return {"prio": prio, "typ": "person", "domain": "", "company": (company or "").strip(),
            "persona": "", "first_name": first, "last_name": last, "title": (title or "").strip()[:120],
            "linkedin_url": url, "rolle_committee": "", "email_track": "",
            "letzter_kommentar_am": "", "kommentar_anzahl": "", "source": source}


def load_block(src_dir: str) -> set:
    """Gesperrte Firmen (Wettbewerber, Richard 15.09.2026) aus BLOCK_FILE, ein
    Firmenname je Zeile, Vergleich ohne Gross/Klein und Mehrfach-Leerzeichen.
    Liegt im gitignored Quellordner, damit ein Neuaufbau sie nicht zurueckholt."""
    path = os.path.join(src_dir, BLOCK_FILE)
    if not os.path.exists(path):
        return set()
    return {" ".join(line.lower().split()) for line in open(path, encoding="utf-8") if line.strip()}


def build(src_dir: str, out_path: str) -> list:
    """Alle Quellen lesen, mischen, schreiben. Rueckgabe: die Zeilen in Reihenfolge."""
    rows, seen = [], set()
    block = load_block(src_dir)

    def add(row):
        k = _key(row["linkedin_url"])
        if " ".join(row["company"].lower().split()) in block:
            return
        if k and k not in seen:
            seen.add(k)
            rows.append(row)

    for f in sorted(glob.glob(os.path.join(src_dir, "hubspot_warm_*.json"))):
        for c in json.load(open(f, encoding="utf-8")):
            add(_row("1", c.get("url", ""), c.get("name", ""), c.get("title", ""), c.get("company", ""),
                     "hubspot_warm"))
    for f in sorted(glob.glob(os.path.join(src_dir, "sn_poster_*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if not d.get("urn") or not ICP_TITLE.search(d.get("title", "")):
                continue
            add(_row("2", f"https://www.linkedin.com/in/{d['urn']}", d.get("person-name", ""),
                     d.get("title", ""), d.get("company-name", ""), "sn_poster"))
    for f in sorted(glob.glob(os.path.join(src_dir, "pool_active_*.json"))):
        for c in json.load(open(f, encoding="utf-8")):
            add(_row("3", c.get("url", ""), c.get("name", ""), c.get("title", ""), c.get("company", ""),
                     "pool_active"))

    rows.sort(key=lambda r: (r["prio"], r["last_name"], r["first_name"]))
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return rows


def push(rows: list, client: str = "jolly") -> int:
    """Upsert nach Supabase (tools/watchlist_db). Die CSV bleibt lokal."""
    from tools.watchlist_db import upsert_watchlist
    return upsert_watchlist(client, rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--push", action="store_true", help="Upsert nach Supabase comment_watchlist")
    args = ap.parse_args(argv)
    rows = build(args.src, args.out)
    by_prio = {}
    for r in rows:
        by_prio[r["prio"]] = by_prio.get(r["prio"], 0) + 1
    print(f"{len(rows)} Personen -> {args.out}; je Prio: {by_prio}")
    if args.push:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT, ".env"))
        print(f"Supabase: {push(rows)} Zeilen upserted (client jolly)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
