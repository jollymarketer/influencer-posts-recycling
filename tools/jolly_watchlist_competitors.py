"""Wettbewerber in Jollys Kommentar-Watchlist finden (Richard 15.09.2026).

Anlass: Kommentar-Entwuerfe auf Posts von Konver und Pangea Summit, beide
Anbieter fuer Vertrieb/GTM statt Kaeufer. Die Sales-Navigator-Branchen
"Software Development" und "IT Services" enthalten solche Anbieter, und die
Watchlist hat keine Spalte, was eine Firma verkauft.

Je Firma eine Google-Suche (Serper), dann ordnet Haiku in Bloecken ein, nach
derselben Definition wie das Relevanz-Gate (abm_comment_drafts.COMPETITOR_RULE).
Ergebnis ist eine CSV zur Durchsicht; geloescht wird hier nichts.

Cache je Firma (Suchtreffer und Urteil) unter clients/jolly/watchlist/, damit
ein Abbruch nicht doppelt zahlt. Fehlgeschlagene Suchen werden nicht gecacht.
Harter Kostendeckel: --max-usd (Serper 0,001 USD je Suche, Haiku nach Usage).

Aufruf: python tools/jolly_watchlist_competitors.py [--limit N] [--max-usd 3.2]
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WL_DIR = os.path.join(ROOT, "clients", "jolly", "watchlist")
CACHE = os.path.join(WL_DIR, "competitor_check_cache.jsonl")
OUT = os.path.join(WL_DIR, "competitor_check_2026-09-15.csv")

SERPER_URL = "https://google.serper.dev/search"
COST_SERPER = 0.001
HAIKU_IN, HAIKU_OUT = 1.0 / 1e6, 5.0 / 1e6
BATCH = 20

CLASSIFY_PROMPT = """Du ordnest Firmen ein. Für jede Firma bekommst du den Namen, einen Jobtitel einer Person dort und Google-Treffer zur Firma.

Frage je Firma: Was verkauft die Firma ihren Kunden, und ist sie damit Wettbewerber einer B2B-Agentur für Vertrieb, Marketing und Go-to-Market?
{rule}

Wenn die Treffer nicht eindeutig zu dieser Firma passen (Namensvetter, nichts gefunden), setze "sicher": false.

FIRMEN:
{items}

Antworte NUR mit einem JSON-Array, ein Objekt je Firma in derselben Reihenfolge:
[{{"id": <id>, "verkauft": "<3 bis 8 Wörter>", "wettbewerber": true oder false, "sicher": true oder false}}]"""


def norm(company: str) -> str:
    return " ".join((company or "").lower().split())


def load_cache() -> dict:
    cache = {}
    if os.path.exists(CACHE):
        for line in open(CACHE, encoding="utf-8"):
            if line.strip():
                d = json.loads(line)
                cache.setdefault(d["key"], {}).update(d)
    return cache


def append_cache(entry: dict) -> None:
    with open(CACHE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def companies_from(rows: list) -> dict:
    """Firmen-Schluessel -> Name, Beispieltitel, Personenzahl. Leere Namen fallen raus."""
    out = defaultdict(lambda: {"company": "", "title": "", "personen": 0})
    for r in rows:
        key = norm(r.get("company"))
        if not key:
            continue
        c = out[key]
        c["company"] = c["company"] or r["company"].strip()
        c["title"] = c["title"] or (r.get("title") or "")
        c["personen"] += 1
    return dict(out)


def serper_snippets(company: str, key: str) -> str | None:
    """Knowledge Graph plus Top-Treffer als kurzer Text. None bei Fehler."""
    try:
        resp = requests.post(SERPER_URL, headers={"X-API-KEY": key},
                             json={"q": f'"{company}"', "gl": "de", "num": 5}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return None
    parts = []
    kg = data.get("knowledgeGraph") or {}
    if kg:
        parts.append(f"KG: {kg.get('title', '')} | {kg.get('type', '')} | {kg.get('description', '')}")
    for o in (data.get("organic") or [])[:5]:
        parts.append(f"{o.get('title', '')} | {o.get('snippet', '')}")
    return "\n".join(parts)[:900]


def parse_batch(raw: str, ids: list) -> dict:
    """JSON-Array des Modells -> id -> Urteil. Unlesbares faellt weg (nicht gecacht)."""
    start, end = (raw or "").find("["), (raw or "").rfind("]")
    if start < 0 or end < 0:
        return {}
    try:
        items = json.loads(raw[start:end + 1])
    except ValueError:
        return {}
    out = {}
    for it in items:
        if isinstance(it, dict) and it.get("id") in ids and isinstance(it.get("wettbewerber"), bool):
            out[it["id"]] = {"verkauft": str(it.get("verkauft") or "")[:120],
                             "wettbewerber": it["wettbewerber"],
                             "sicher": bool(it.get("sicher"))}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="nur die ersten N Firmen (Probelauf)")
    ap.add_argument("--only", default="", help="kommagetrennte Firmennamen (Probelauf mit bekannten Faellen)")
    ap.add_argument("--max-usd", type=float, default=3.2)
    args = ap.parse_args(argv)

    from dotenv import dotenv_values, load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    serper_key = (os.environ.get("SERPER_API_KEY")
                  or dotenv_values(os.path.join(ROOT, "..", "..", ".env")).get("SERPER_API_KEY"))
    from clients import load_client
    from tools.abm_comment_drafts import COMPETITOR_RULE, GATE_MODEL
    from tools.anthropic_auth import LazyAnthropic
    from tools.watchlist_db import get_watchlist

    comps = companies_from(get_watchlist("jolly"))
    keys = sorted(comps)[: args.limit or None]
    if args.only:
        keys = [k for k in keys if k in {norm(x) for x in args.only.split(",")}]
    cache = load_cache()
    spent = 0.0

    todo = [k for k in keys if "snippets" not in cache.get(k, {})]
    print(f"{len(keys)} Firmen, {len(todo)} ohne Suchtreffer im Cache.")
    if len(todo) * COST_SERPER > args.max_usd:
        print("Abbruch: Suche allein ueber dem Deckel.")
        return 1
    with ThreadPoolExecutor(max_workers=10) as pool:
        for k, snip in zip(todo, pool.map(lambda k: serper_snippets(comps[k]["company"], serper_key), todo)):
            if snip is None:
                continue
            spent += COST_SERPER
            cache.setdefault(k, {"key": k}).update(snippets=snip)
            append_cache({"key": k, "snippets": snip})
    print(f"Suche fertig, Kosten bisher {spent:.2f} USD.")

    llm = LazyAnthropic(load_client())
    todo = [k for k in keys if "wettbewerber" not in cache.get(k, {}) and "snippets" in cache.get(k, {})]
    for i in range(0, len(todo), BATCH):
        if spent >= args.max_usd:
            print(f"Deckel erreicht bei {spent:.2f} USD, Rest bleibt offen.")
            break
        chunk = todo[i:i + BATCH]
        items = "\n\n".join(f"id {n}: {comps[k]['company']} (Titel: {comps[k]['title']})\n{cache[k]['snippets']}"
                            for n, k in enumerate(chunk))
        resp = llm.messages.create(model=GATE_MODEL, max_tokens=4000, messages=[{
            "role": "user", "content": CLASSIFY_PROMPT.format(rule=COMPETITOR_RULE, items=items)}])
        spent += resp.usage.input_tokens * HAIKU_IN + resp.usage.output_tokens * HAIKU_OUT
        for n, verdict in parse_batch(resp.content[0].text, list(range(len(chunk)))).items():
            cache[chunk[n]].update(verdict)
            append_cache({"key": chunk[n], **verdict})
        print(f"  Block {i // BATCH + 1}: {min(i + BATCH, len(todo))}/{len(todo)}, {spent:.2f} USD")

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["firma", "personen", "wettbewerber", "sicher", "verkauft", "beispiel_titel"])
        for k in keys:
            c = cache.get(k, {})
            w.writerow([comps[k]["company"], comps[k]["personen"], c.get("wettbewerber", ""),
                        c.get("sicher", ""), c.get("verkauft", ""), comps[k]["title"]])
    hits = [k for k in keys if cache.get(k, {}).get("wettbewerber") is True]
    open_ = [k for k in keys if "wettbewerber" not in cache.get(k, {})]
    print(f"Wettbewerber: {len(hits)} Firmen, {sum(comps[k]['personen'] for k in hits)} Personen; "
          f"ohne Urteil: {len(open_)}; Kosten dieses Laufs ~{spent:.2f} USD -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
