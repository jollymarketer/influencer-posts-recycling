"""Stimmen-Discovery: Einzelpersonen aus dem Keyword-Scrape gewinnen.

Warum (Richard, 19.08.2026): Verbaende, Kammern und Kanzleien findet man ueber
die Websuche. Einzelne Beraterinnen und Berater nicht - die haben keine
Pressemitteilungen und keinen Wikipedia-Eintrag. Sie stehen aber als Autor unter
jedem Fachbeitrag, den der Keyword-Scrape ohnehin einsammelt.

Der Lauf sucht also nicht nach Personen, sondern nach Themen, und liest ab, wer
zu diesen Themen schreibt. Wer mehrfach auftaucht, ist eine Stimme.

Aufruf (kostet einen Apify-Lauf, Spend-Gate beachten):

    CLIENT=swot python -m tools.discover_voices --max-posts 30 --min-posts 2
    CLIENT=swot python -m tools.discover_voices --keywords "Liquiditaetsplanung" --max-posts 5

Ausgabe ist eine CSV mit Kandidaten im Format von influencers.csv. Sie wird NICHT
automatisch uebernommen - die Liste ist ein Vorschlag, ueber den Richard und der
Kunde entscheiden.
"""
import argparse
import csv
import io
import os
import sys
from collections import defaultdict

# Gesperrte Anbieter (Christian Kulle, 13.08.2026) plus die von uns ergaenzten.
# Gilt fuer jeden Anbieter konkurrierender Planungs-, Konsolidierungs- oder
# Liquiditaetssoftware, deshalb zusaetzlich generische Produktbegriffe.
VENDOR_TERMS = {
    "jedox", "lucanet", "corporate planning", "corporate planner", "agicap",
    "tidely", "idl", "prevero", "unit4", "cubus", "swot controlling",
    "anaplan", "board international", "pigment", "workday adaptive",
    "oracle epm", "sap analytics cloud", "onestream", "vena solutions",
    "planungssoftware", "controlling-software", "controlling software",
    "epm software", "cpm software", "fp&a software",
}


def is_vendor(name: str, headline: str) -> bool:
    """True, wenn Name oder Headline auf einen Softwareanbieter zeigt."""
    haystack = f"{name or ''} {headline or ''}".lower()
    return any(term in haystack for term in VENDOR_TERMS)


def aggregate_authors(posts: list, min_posts: int = 2) -> list:
    """Autoren nach Haeufigkeit und Viralitaet buendeln, Vendor-Treffer raus.

    Autoren ohne Profil-URL fallen weg: ohne URL laesst sich niemand in
    influencers.csv eintragen, und ein Name allein ist nicht eindeutig.
    """
    bucket = defaultdict(lambda: {"posts": 0, "virality_sum": 0, "name": "", "headline": ""})
    for p in posts:
        url = (p.get("author_url") or "").strip()
        if not url:
            continue
        name = p.get("influencer") or ""
        headline = p.get("author_headline") or ""
        if is_vendor(name, headline):
            continue
        e = bucket[url]
        e["posts"] += 1
        e["virality_sum"] += int(p.get("virality") or 0)
        e["name"] = e["name"] or name
        e["headline"] = e["headline"] or headline

    out = [
        {"url": url, "name": v["name"], "headline": v["headline"],
         "posts": v["posts"], "virality_sum": v["virality_sum"]}
        for url, v in bucket.items() if v["posts"] >= min_posts
    ]
    # Haeufigkeit vor Reichweite: wer regelmaessig schreibt, traegt eine Kadenz.
    out.sort(key=lambda r: (r["posts"], r["virality_sum"]), reverse=True)
    return out


def write_candidates(rows: list, path: str) -> None:
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Name", "LinkedIn URL", "Substack URL", "Other Channels"])
        for r in rows:
            note = f"KANDIDAT {r['posts']} Beitraege Viralitaet {r['virality_sum']} | {r['headline']}"
            w.writerow([r["name"], r["url"], "", note.replace("\n", " ")[:300]])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-posts", type=int, default=30, help="Beitraege je Stichwort")
    ap.add_argument("--min-posts", type=int, default=2, help="ab wie vielen Beitraegen ein Autor gilt")
    ap.add_argument("--posted-limit", default="month")
    ap.add_argument("--min-virality", type=int, default=0,
                    help="0 lassen: in der stillen Nische zaehlt Fachlichkeit, nicht Reichweite")
    ap.add_argument("--keywords", nargs="*", help="Teilmenge, fuer guenstige Probelaeufe")
    ap.add_argument("--out", default="kandidaten_stimmen.csv")
    args = ap.parse_args()

    from clients import load_client
    from run_keyword_scrape import resolve_keywords
    from tools.linkedin_keyword_scraper import scrape_keyword_posts

    client = os.getenv("CLIENT", "jolly").strip().lower()
    keywords = args.keywords or resolve_keywords(load_client(), client)

    print(f"Discovery fuer '{client}': {len(keywords)} Stichworte, "
          f"max {args.max_posts} Beitraege je Stichwort.", flush=True)
    posts = scrape_keyword_posts(
        keywords, max_posts=args.max_posts, posted_limit=args.posted_limit,
        min_virality=args.min_virality, author_keywords="",
    )
    print(f"  {len(posts)} Beitraege eingesammelt.")

    ohne_url = sum(1 for p in posts if not (p.get("author_url") or "").strip())
    if ohne_url:
        print(f"  Hinweis: {ohne_url} Beitraege ohne Autoren-URL, fallen raus.")

    rows = aggregate_authors(posts, min_posts=args.min_posts)
    print(f"  {len(rows)} Kandidaten mit mindestens {args.min_posts} Beitraegen.")
    write_candidates(rows, args.out)
    print(f"  geschrieben: {args.out}")
    for r in rows[:20]:
        print(f"    {r['posts']:3d} Beitraege  v{r['virality_sum']:3d}  {r['name']}  {r['headline'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
