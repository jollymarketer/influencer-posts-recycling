"""Achsen-Deckel fuer die Tages-Auswahl.

Reine Funktionen, kein Netz: run_research.py holt das Fenster aus Notion und
den Pool aus Supabase und gibt beides hier hinein. Der Deckel wirkt auf der
Ausgabeseite, weil 81 Prozent von jollys Pool Profil-Scrape ohne
Achsen-Herkunft sind (gemessen 22.09.2026) -- eine Mischregel beim Scrapen
allein erreicht diese Zeilen nicht.
"""
CAP = 2
MIN_POOL_TEXT = 200

_AXIS_SOURCE_PREFIX = "linkedin_search:"


def axis_of(post: dict) -> str | None:
    """Achse einer Zeile. Spalte `axis` gewinnt, danach der source-Prefix
    (Zeilen aus run_axis_scrape.py vor dem Backfill)."""
    achse = post.get("axis")
    if achse:
        return achse
    source = post.get("source", "") or ""
    if source.startswith(_AXIS_SOURCE_PREFIX):
        rest = source[len(_AXIS_SOURCE_PREFIX):].strip()
        return rest or None
    return None


def blocked_axes(recent: list, cap: int = CAP) -> set:
    """Achsen, die im Fenster schon `cap` mal vorkommen. 'null' zaehlt nie:
    ein Post ohne Achse darf keine Achse sperren."""
    zaehler = {}
    for achse in recent:
        if not achse or achse == "null":
            continue
        zaehler[achse] = zaehler.get(achse, 0) + 1
    return {a for a, n in zaehler.items() if n >= cap}


def free_candidates(posts: list, blocked: set) -> list:
    """Kandidaten ausserhalb der gesperrten Achsen. Reihenfolge bleibt, der
    Aufrufer hat schon nach Score sortiert. axis=None gilt als frei."""
    return [p for p in posts if axis_of(p) not in blocked]


def pool_candidates(rows: list, blocked: set, seen_urls: set) -> list:
    """Supabase-Zeilen, die als Rueckgriff taugen: freie Achse, nicht schon
    gesehen, genug Text zum Scoren."""
    raus = []
    for row in rows:
        url = row.get("post_url")
        if not url or url in seen_urls:
            continue
        if axis_of(row) in blocked:
            continue
        if len(row.get("post_text", "") or "") < MIN_POOL_TEXT:
            continue
        raus.append(row)
    return raus
