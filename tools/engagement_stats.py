"""Auswertung der zurueckgeschriebenen Engagement-Zahlen.

Der Readback (tools/engagement_readback.py) schreibt Likes/Kommentare/Shares
in die Notion-Zeile und endete dort - die Zahlen lagen als Sackgasse in der DB.
Dieses Modul aggregiert sie entlang der Entscheidungen, die die Pipeline pro
Post trifft (Format, Persona, Bild-Variante, Infografik-Typ, Matrix-Box), und
sagt vor allem: ob die Stichprobe fuer eine Aussage ueberhaupt reicht.

Zwei bewusste Entscheidungen:

1. Median statt Mittelwert. LinkedIn-Engagement hat einen schweren Rand: ein
   einzelner viraler Post zieht den Mittelwert einer Zelle so weit hoch, dass
   die Rangfolge nur noch diesen einen Post abbildet.
2. Stichproben-Gate. Unter MIN_POSTS_PER_CELL Posts je Zelle kippt schon ein
   Ausreisser die Reihenfolge. Solange das Gate zu ist, liefert dieses Modul
   bewusst KEINE Gewinner-Aussage, sondern nur den Abstand bis dahin. Ein
   Muster aus vier Posts ist kein Muster.
"""
import statistics

# Gewichtung wie im Top-Listing von engagement_readback: ein Kommentar kostet
# mehr Aufmerksamkeit als ein Like, ein Share mehr als ein Kommentar.
ENGAGEMENT_WEIGHTS = {"likes": 1, "comments": 2, "shares": 3}

MIN_POSTS_PER_CELL = 5
MIN_CELLS_PER_DIMENSION = 2

# Stichprobengroesse allein reicht nicht: bei Medianen von 0 und 1 ist der
# "Sieger" eine einzelne Reaktion einer einzelnen Person. Ein Abstand unter
# einem Kommentar plus einem Like (2 + 1 Punkte) ist nicht unterscheidbar von
# Zufall, egal wie voll die Zellen sind.
MIN_MEDIAN_SPREAD = 3

UNSET = "(ohne Wert)"


def engagement_score(row: dict) -> int | None:
    """Gewichteter Score. None, wenn der Post nie gemessen wurde - eine
    ungemessene Zeile ist nicht dasselbe wie eine Zeile mit null Likes."""
    values = [row.get(k) for k in ENGAGEMENT_WEIGHTS]
    if all(v is None for v in values):
        return None
    return sum(int(row.get(k) or 0) * w for k, w in ENGAGEMENT_WEIGHTS.items())


def measured_rows(rows: list) -> list:
    """Zeilen mit Messwert, jeweils um `score` ergaenzt."""
    out = []
    for row in rows:
        score = engagement_score(row)
        if score is not None:
            out.append({**row, "score": score})
    return out


def aggregate(rows: list, dimensions: tuple = ()) -> dict:
    """{Dimension: [Zelle, ...]} - Zellen absteigend nach Median.

    Zelle: value, n, median, mean, best. Erwartet Zeilen mit `dims` (siehe
    notion_db.get_published_rows) und einem gemessenen Engagement.
    """
    measured = measured_rows(rows)
    dims = dimensions or tuple(sorted(
        {d for r in measured for d in (r.get("dims") or {})}))
    stats = {}
    for dim in dims:
        buckets: dict[str, list[int]] = {}
        for row in measured:
            value = (row.get("dims") or {}).get(dim) or UNSET
            buckets.setdefault(value, []).append(row["score"])
        cells = [{
            "value": value,
            "n": len(scores),
            "median": statistics.median(scores),
            "mean": sum(scores) / len(scores),
            "best": max(scores),
        } for value, scores in buckets.items()]
        cells.sort(key=lambda c: (c["median"], c["n"]), reverse=True)
        stats[dim] = cells
    return stats


def evaluable_cells(cells: list, min_n: int = MIN_POSTS_PER_CELL) -> list:
    """Zellen, die gross genug fuer einen Vergleich sind. `(ohne Wert)` faellt
    raus: eine fehlende Property ist keine Entscheidung der Pipeline und kann
    deshalb auch keine Empfehlung sein (lisocon: 6 Altposts ohne Matrix-Box)."""
    return [c for c in cells if c["n"] >= min_n and c["value"] != UNSET]


def gate_open(cells: list, min_n: int = MIN_POSTS_PER_CELL,
              min_cells: int = MIN_CELLS_PER_DIMENSION) -> bool:
    """Vergleichen darf man erst, wenn mindestens `min_cells` Zellen je
    `min_n` Posts tragen. Sonst vergleicht man Rauschen mit Rauschen."""
    return len(evaluable_cells(cells, min_n)) >= min_cells


def shortfall(cells: list, min_n: int = MIN_POSTS_PER_CELL,
              min_cells: int = MIN_CELLS_PER_DIMENSION) -> int:
    """Wie viele veroeffentlichte Posts noch fehlen, bis die Dimension
    auswertbar ist. Zaehlt die guenstigsten Zellen, also die bereits
    groessten - der schnellste Weg zum offenen Gate."""
    if gate_open(cells, min_n, min_cells):
        return 0
    largest = sorted((c["n"] for c in cells if c["value"] != UNSET),
                     reverse=True)[:min_cells]
    largest += [0] * (min_cells - len(largest))
    return sum(max(0, min_n - n) for n in largest)


def verdict(cells: list, min_n: int = MIN_POSTS_PER_CELL,
            min_cells: int = MIN_CELLS_PER_DIMENSION,
            min_spread: float = MIN_MEDIAN_SPREAD) -> dict | None:
    """Bester und schwaechster auswertbarer Wert einer Dimension - oder None,
    wenn die Stichprobe zu duenn ODER der Abstand zu klein ist. Beide Gates
    muessen offen sein; volle Zellen mit einem Punkt Abstand sind kein Befund."""
    usable = evaluable_cells(cells, min_n)
    if len(usable) < min_cells:
        return None
    spread = usable[0]["median"] - usable[-1]["median"]
    if spread < min_spread:
        return None
    return {"best": usable[0], "worst": usable[-1], "spread": spread}


def report_lines(stats: dict, min_n: int = MIN_POSTS_PER_CELL,
                 min_cells: int = MIN_CELLS_PER_DIMENSION,
                 min_spread: float = MIN_MEDIAN_SPREAD) -> list:
    """Menschenlesbarer Report. Zeigt IMMER alle Zellen, damit sichtbar ist,
    wo sich die Stichprobe gerade fuellt - und nennt bei geschlossenem Gate
    den Grund, damit niemand aus einer Rangfolge liest, was sie nicht traegt."""
    lines = []
    for dim, cells in stats.items():
        total = sum(c["n"] for c in cells)
        head = f"  {dim} (n={total})"
        result = verdict(cells, min_n, min_cells, min_spread)
        if result:
            head += (f" — auswertbar: {result['best']['value']} liegt vorn"
                     f" (Median {result['best']['median']:g} vs."
                     f" {result['worst']['value']} {result['worst']['median']:g})")
        elif gate_open(cells, min_n, min_cells):
            usable = evaluable_cells(cells, min_n)
            spread = usable[0]["median"] - usable[-1]["median"]
            head += (f" — Stichprobe reicht, Abstand nicht:"
                     f" Median-Spanne {spread:g} < {min_spread:g}")
        else:
            need = shortfall(cells, min_n, min_cells)
            head += f" — noch nicht auswertbar, es fehlen ~{need} veroeffentlichte Posts"
        lines.append(head)
        for cell in cells:
            mark = "*" if cell["n"] >= min_n else " "
            lines.append(f"    {mark} {cell['value']:<22} n={cell['n']:<3}"
                         f" Median {cell['median']:<7.1f} Bester {cell['best']}")
    return lines


def summary_line(rows: list) -> str:
    measured = measured_rows(rows)
    return (f"  {len(measured)}/{len(rows)} veroeffentlichte Zeilen tragen"
            f" Engagement-Zahlen.")


if __name__ == "__main__":
    # Nur-Lese-Blick auf den aktuellen Stand: eine Notion-Query, kein Scrape,
    # kein Schreiben, keine Kosten. Der Import liegt bewusst hier, damit das
    # Modul selbst importierbar bleibt, ohne Notion-Env zu brauchen.
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from clients import load_client
    from tools.notion_db import ENGAGEMENT_DIMENSIONS, get_published_rows

    published = get_published_rows()
    print(f"Engagement-Auswertung (Client: {load_client().NAME})")
    print(summary_line(published))
    for line in report_lines(aggregate(published, ENGAGEMENT_DIMENSIONS)):
        print(line)
