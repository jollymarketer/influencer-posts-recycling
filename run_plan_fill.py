"""Redaktionsplan fuellen: Termin, Kanal, Bezug und Beitragstext.

    CLIENT=swot python run_plan_fill.py --months 2026-09 2026-10          # Trockenlauf
    CLIENT=swot python run_plan_fill.py --months 2026-09 2026-10 --write  # schreibt

Der Monatsplan (run_monthly_plan.py) legt Themenvorschlaege NEU an. Dieses
Skript arbeitet auf den Zeilen, die schon im Plan stehen: es verteilt sie auf
die Slots der aktiven Konten und schreibt den Text dazu.

Zwei Regeln, beide bewusst:

1. Status geht auf "Entwurf", nie weiter. Die Kette (Richard 21.08.2026):
   Kunde setzt "Text freigegeben" nach dem Lesen; run_image_fill baut das
   Bild und setzt "Text+Bild"; Kunde prueft Text und Bild zusammen und setzt
   "Freigegeben"; das Posten (Make, noch nicht gebaut) setzt "Gepostet" und
   fuellt "Geposted am". Dieses Skript setzt nur "Entwurf".
2. Ein Text wird nur neu geschrieben, wenn die Zeile das Konto wechselt oder
   noch keinen Text hat. Der Text traegt die Stimme des Kontos, ein Wir-Text
   der Unternehmensseite passt nicht unter Roberts Namen.

Seit 20.08.2026 laeuft der Text durch die volle DACH-Maschinerie
(tools/post_writer.py): Format-Router mit Anti-Repeat je Kanal, Persona der
Achse, Soundbyte und Infografik-Skelett landen als eigene Properties in der
Zeile. Die drei Properties (Format, Soundbyte, Infografik-Skelett) legt
scripts/add_plan_fill_properties.py an; in den Kunden-Views ausblenden.
"""
import argparse
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from clients import load_client
from tools.monthly_plan import (
    NOTION_API,
    TIMEOUT,
    Topic,
    axis_id,
    build_slots,
    select,
)
from tools import content_matrix as cm
from tools.post_scorer import (
    normalize_infographic_type,
    parse_infographic_type,
    pick_format,
)
from tools.naturalness import phrases as used_phrases
from tools.post_writer import length_band_for, write_post
from tools.topic_ideas_db import _headers as notion_headers

BEZUG = "Basis"

# Notion deckelt einen rich_text-Baustein bei 2000 UTF-16-Einheiten; der alte
# harte Schnitt bei 1990 Zeichen kappte jeden Story-Post. Jetzt Chunks.
_CHUNK_LIMIT = 1990


def _chunks(text: str, limit: int = _CHUNK_LIMIT) -> list[str]:
    """Zerlegt Text in Stuecke von hoechstens `limit` UTF-16-Einheiten
    (Notion-Mass; Emojis zaehlen doppelt). Verlustfrei: join == Original."""
    out, cur, units = [], [], 0
    for ch in text:
        u = len(ch.encode("utf-16-le")) // 2
        if units + u > limit:
            out.append("".join(cur))
            cur, units = [], 0
        cur.append(ch)
        units += u
    if cur:
        out.append("".join(cur))
    return out or [""]


def _rich(text: str) -> dict:
    return {"rich_text": [{"text": {"content": c}} for c in _chunks(text)]}


def _title(props, key="Titel") -> str:
    return "".join(x.get("plain_text", "") for x in (props.get(key) or {}).get("title", []))


def _rt(props, key) -> str:
    return "".join(x.get("plain_text", "") for x in (props.get(key) or {}).get("rich_text", []))


def _sel(props, key):
    return ((props.get(key) or {}).get("select") or {}).get("name")


def read_plan(db_id: str) -> list[dict]:
    rows, cur = [], None
    while True:
        payload = {"page_size": 100}
        if cur:
            payload["start_cursor"] = cur
        resp = requests.post(f"{NOTION_API}/databases/{db_id}/query",
                             headers=notion_headers(), json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        j = resp.json()
        rows += j["results"]
        if not j.get("has_more"):
            break
        cur = j["next_cursor"]
    return rows


def plan_topics(rows: list[dict]) -> tuple[list[Topic], dict]:
    """Plan-Zeilen mit Achse als Topic-Objekte, plus Nachschlagewerk je Seite."""
    topics, meta = [], {}
    for r in rows:
        p = r["properties"]
        achse = axis_id(_sel(p, "Achse"))
        if not achse:
            continue
        titel = _title(p)
        topics.append(Topic(page_id=r["id"], title=titel, title_de=titel,
                            keyword_de="", score=0, axis=achse, evidence=""))
        meta[r["id"]] = {
            "titel": titel,
            "achse": achse,
            "kurz": _rt(p, "Kurzbeschreibung"),
            "kanal_alt": _sel(p, "Kanal"),
            "hat_text": bool(_rt(p, "Post-Text")),
        }
    return topics, meta


def _date(props, key="Geplant für") -> str:
    return (((props.get(key) or {}).get("date")) or {}).get("start") or ""


def _format_history(rows: list[dict]) -> dict:
    """Bereits vergebene Formate je Kanal aus dem Plan, neuestes zuerst.

    Ohne diese Vorgeschichte startet jeder Lauf mit leerem Fenster; die
    Matrix-Quota braucht aber mindestens fuenf klassifizierte Beitraege und
    griffe dann nie. Zeilen ohne Format bleiben draussen, sie wuerden das
    Fenster nur verkuerzen."""
    hist: dict[str, list] = {}
    for r in sorted(rows, key=lambda r: _date(r["properties"]), reverse=True):
        p = r["properties"]
        fmt, kanal = _sel(p, "Format"), _sel(p, "Kanal")
        if fmt and kanal:
            hist.setdefault(kanal, []).append(fmt)
    return hist


def _asset_history(rows: list[dict], cfg) -> list:
    """Zuletzt verbrauchte Belege als LRU-Liste, neuestes zuerst.

    Der Plan speichert das Asset nicht, wohl aber das Format. Aus der Zahl
    der vorhandenen CaseProof-Zeilen laesst sich die Position im Zyklus
    rekonstruieren, damit ueber Monate alle Faelle drankommen statt immer
    des ersten."""
    ids = [a["id"] for a in getattr(cfg, "PROOF_ASSETS", None) or []]
    if not ids:
        return []
    n = sum(1 for r in rows if _sel(r["properties"], "Format") == "CaseProof")
    return list(reversed(ids[:n % len(ids)]))


def _choose_format(cfg, material: str, fmts: list, used_assets: list):
    """Format und Beleg fuer eine Zeile: erst die Ziel-Box, dann das Format.

    Liefert die Matrix (Proof, Selection), ist CaseProof Pflicht und der
    Beitrag traegt einen echten Fall aus PROOF_ASSETS. Sonst laeuft der freie
    Pool, aus dem die Asset-Formate bewusst ausgeschlossen sind. Ohne MATRIX
    in der Mandanten-Config bleibt es bei den vier Legacy-Formaten."""
    boxes = [cm.FORMAT_TO_BOX[f] for f in fmts if f in cm.FORMAT_TO_BOX]
    target = cm.pick_target_box(boxes, cfg)
    kandidaten = cm.formats_for_box(target, cfg) if target else cm.free_formats(cfg)
    fmt = pick_format({"influencer": "Plan", "post_text": material},
                      list(fmts), kandidaten)
    return fmt, cm.asset_for_format(fmt, cfg, used_assets)


def text_fill(months: list[tuple[int, int]], cfg=None, rewrite: bool = False) -> dict:
    """Textet Plan-Zeilen der genannten Monate, ohne Termine oder Kanaele
    anzufassen. Ketten-Schritt hinter run_monthly_plan: die Zeilen sind dort
    bereits geslottet, hier fehlt nur der Beitragstext. fill() dagegen
    verteilt ALLE Zeilen neu auf Slots und darf nie hinter write_proposals
    laufen, sonst datiert es Bestandsmonate um."""
    cfg = cfg or load_client()
    month_keys = {f"{y:04d}-{m:02d}" for y, m in months}
    rows = read_plan(cfg.CONTENT_PLAN_DB_ID)
    kandidaten = []
    for r in rows:
        p = r["properties"]
        datum = _date(p)
        achse = axis_id(_sel(p, "Achse"))
        if datum[:7] not in month_keys or not achse:
            continue
        kandidaten.append({
            "page_id": r["id"], "datum": datum, "achse": achse,
            "kanal": _sel(p, "Kanal"), "titel": _title(p),
            "kurz": _rt(p, "Kurzbeschreibung"),
            "hat_text": bool(_rt(p, "Post-Text")),
        })
    kandidaten.sort(key=lambda k: k["datum"])
    print(f"Zeilen in {sorted(month_keys)}: {len(kandidaten)}")

    geschrieben = 0
    # Formate aus dem Bestand vorladen: Anti-Repeat und Matrix-Fenster
    # brauchen die Vorgeschichte, das Laengenband zaehlt dagegen nur die in
    # diesem Lauf geschriebenen Beitraege.
    recent_formats: dict[str, list] = _format_history(rows)
    recent_types: dict[str, list] = {}
    neu_je_kanal: dict[str, int] = {}
    used_assets = _asset_history(rows, cfg)
    # Verbrauchte Formulierungen je Kanal (tools/naturalness.phrases): ein
    # Konto zitiert sich sonst von Post zu Post selbst.
    used: dict[str, list] = {}
    for k in kandidaten:
        if k["hat_text"] and not rewrite:
            print(f"  {k['datum']} {k['kanal']:20s} alt {k['titel'][:55]}", flush=True)
            continue
        material = f"{k['titel']}\n{k['kurz']}"
        fmts = recent_formats.setdefault(k["kanal"], [])
        typs = recent_types.setdefault(k["kanal"], [])
        fmt, asset = _choose_format(cfg, material, fmts, used_assets)
        band = length_band_for(cfg, neu_je_kanal.get(k["kanal"], 0))
        r = write_post(k["titel"], k["kurz"], k["kanal"], k["achse"],
                       post_format=fmt, recent_infographic_types=list(typs), cfg=cfg,
                       band=band, avoid_phrases=list(used.get(k["kanal"], [])),
                       datum=k["datum"], asset=asset)
        if not r["text"]:
            print(f"  {k['datum']} kein Text erhalten, Zeile uebersprungen")
            continue
        if asset and not cm.figures_ok(r["text"], asset):
            print(f"  {k['datum']} Zahlen-Guard: Zahl ohne Beleg im Asset "
                  f"'{asset['id']}', Zeile uebersprungen")
            continue
        used.setdefault(k["kanal"], []).extend(used_phrases(r["text"]))
        props = {
            "Status": {"select": {"name": "Entwurf"}},
            "Bezug": {"select": {"name": BEZUG}},
            "Post-Text": _rich(r["text"]),
            "Format": {"select": {"name": fmt}},
            "Soundbyte": _rich(r["soundbyte"]),
            "Infografik-Skelett": _rich(r["skeleton"]),
        }
        resp = requests.patch(f"{NOTION_API}/pages/{k['page_id']}",
                              headers=notion_headers(), json={"properties": props},
                              timeout=TIMEOUT)
        if resp.ok:
            geschrieben += 1
            fmts.insert(0, fmt)
            neu_je_kanal[k["kanal"]] = neu_je_kanal.get(k["kanal"], 0) + 1
            if asset:
                used_assets.insert(0, asset["id"])
            ityp = normalize_infographic_type(parse_infographic_type(r["skeleton"]))
            if ityp:
                typs.insert(0, ityp)
            print(f"  {k['datum']} {k['kanal']:20s} NEU {fmt}/{band or 'format'} "
                  f"{k['titel'][:55]}", flush=True)
        else:
            print(f"  Notion-Fehler {resp.status_code}: {resp.text[:160]}")
    return {"zeilen": len(kandidaten), "geschrieben": geschrieben}


def fill(months: list[tuple[int, int]], write: bool = False, cfg=None,
         rewrite: bool = False) -> dict:
    cfg = cfg or load_client()
    rows = read_plan(cfg.CONTENT_PLAN_DB_ID)
    topics, meta = plan_topics(rows)
    print(f"Plan-Zeilen mit Achse: {len(topics)}")

    slots = []
    for year, month in months:
        slots += build_slots(year, month)
    print(f"Slots in {len(months)} Monaten, nur aktive Konten: {len(slots)}")

    slots = select(slots, topics, [], cfg.AXIS_MIX, cfg.AXIS_TO_ACCOUNT)
    belegt = [s for s in slots if s.topic]
    print(f"belegt: {len(belegt)} von {len(slots)}")

    gefuellt, neu_geschrieben = 0, 0
    # Anti-Repeat je Kanal (neuestes zuerst): Formate fuer pick_format,
    # Infografik-Typen fuer das Skelett. Die Formate kommen aus dem Bestand,
    # sonst sieht die Matrix in jedem Lauf ein leeres Fenster; die
    # Infografik-Typen bleiben laufintern, ein Monats-Batch entsteht ohnehin
    # in einem Stueck.
    recent_formats: dict[str, list] = _format_history(rows)
    recent_types: dict[str, list] = {}
    neu_je_kanal: dict[str, int] = {}
    used_assets = _asset_history(rows, cfg)
    used: dict[str, list] = {}
    for s in sorted(belegt, key=lambda s: s.day):
        m = meta[s.topic["page_id"]]
        # rewrite erzwingt Neuerstellung (Richard 20.08.2026: Bestandstexte aus
        # dem alten Schlank-Prompt durch die volle Maschinerie ersetzen).
        neu_noetig = rewrite or (not m["hat_text"]) or m["kanal_alt"] != s.kanal
        marke = "NEU" if neu_noetig else "alt"
        print(f"  {s.day} {s.kanal:20s} {marke} {m['titel'][:55]}", flush=True)
        if not write:
            continue
        props = {
            "Geplant für": {"date": {"start": s.day.isoformat()}},
            "Kanal": {"select": {"name": s.kanal}},
            "Bezug": {"select": {"name": BEZUG}},
            "Status": {"select": {"name": "Entwurf"}},
        }
        if neu_noetig:
            fmts = recent_formats.setdefault(s.kanal, [])
            typs = recent_types.setdefault(s.kanal, [])
            material = f"{m['titel']}\n{m['kurz']}"
            fmt, asset = _choose_format(cfg, material, fmts, used_assets)
            band = length_band_for(cfg, neu_je_kanal.get(s.kanal, 0))
            r = write_post(m["titel"], m["kurz"], s.kanal, s.axis,
                           post_format=fmt, recent_infographic_types=list(typs),
                           cfg=cfg, band=band,
                           avoid_phrases=list(used.get(s.kanal, [])),
                           datum=s.day.isoformat(), asset=asset)
            if not r["text"]:
                print(f"    kein Text erhalten, Zeile uebersprungen")
                continue
            if asset and not cm.figures_ok(r["text"], asset):
                print(f"    Zahlen-Guard: Zahl ohne Beleg im Asset "
                      f"'{asset['id']}', Zeile uebersprungen")
                continue
            used.setdefault(s.kanal, []).extend(used_phrases(r["text"]))
            props["Post-Text"] = _rich(r["text"])
            props["Format"] = {"select": {"name": fmt}}
            props["Soundbyte"] = _rich(r["soundbyte"])
            props["Infografik-Skelett"] = _rich(r["skeleton"])
            fmts.insert(0, fmt)
            neu_je_kanal[s.kanal] = neu_je_kanal.get(s.kanal, 0) + 1
            if asset:
                used_assets.insert(0, asset["id"])
            ityp = normalize_infographic_type(parse_infographic_type(r["skeleton"]))
            if ityp:
                typs.insert(0, ityp)
            neu_geschrieben += 1
        resp = requests.patch(f"{NOTION_API}/pages/{s.topic['page_id']}",
                              headers=notion_headers(), json={"properties": props},
                              timeout=TIMEOUT)
        if resp.ok:
            gefuellt += 1
        else:
            print(f"    Notion-Fehler {resp.status_code}: {resp.text[:160]}")

    ohne = [t for t in topics if t.page_id not in {s.topic["page_id"] for s in belegt}]
    for t in ohne:
        print(f"  ohne Termin [{t.axis}] {t.title[:70]}")
    return {"belegt": len(belegt), "gefuellt": gefuellt,
            "neu_geschrieben": neu_geschrieben, "ohne_termin": len(ohne)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", nargs="+", required=True,
                    help="Zielmonate, z.B. 2026-09 2026-10")
    ap.add_argument("--write", action="store_true",
                    help="in Notion schreiben (Default: Trockenlauf)")
    ap.add_argument("--rewrite", action="store_true",
                    help="auch Zeilen mit Bestandstext neu schreiben")
    args = ap.parse_args()
    months = [tuple(int(x) for x in m.split("-")) for m in args.months]

    r = fill(months, write=args.write, rewrite=args.rewrite)
    print(f"\nbelegt {r['belegt']} | geschrieben {r['gefuellt']} | "
          f"Texte neu {r['neu_geschrieben']} | ohne Termin {r['ohne_termin']}")
    if not args.write:
        print("Trockenlauf, nichts geschrieben. Mit --write ausfuehren.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
