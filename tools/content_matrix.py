"""Content-Matrix-Modell (Douwe Wester: 3 Jobs x 3 Stages = 9 Boxen).

Reine Python-Logik ohne LLM: Box-Modell, Mandanten-Whitelist, Quota-Mathe,
Asset-Auswahl und Zahlen-Guard. Spec:
docs/superpowers/specs/2026-07-08-content-matrix-coverage-design.md
"""

import re

JOBS = ("Perspective", "Proof", "Promotion")
STAGES = ("Awareness", "Education", "Selection")

# Box -> Formate. Reihenfolge der Formate = deterministische Fallback-Ordnung.
BOX_FORMATS = {
    ("Perspective", "Awareness"): ("Opinion",),
    ("Perspective", "Education"): ("POV", "Signature"),
    ("Perspective", "Selection"): ("Comparison",),
    ("Proof", "Awareness"): ("Story",),
    ("Proof", "Education"): ("Method",),
    ("Proof", "Selection"): ("CaseProof",),
    ("Promotion", "Awareness"): ("Debate",),
    ("Promotion", "Education"): ("Magnet",),
    ("Promotion", "Selection"): ("Offer",),
}

FORMAT_TO_BOX = {f: box for box, formats in BOX_FORMATS.items() for f in formats}

PROMOTION_FORMATS = tuple(
    f for box, formats in BOX_FORMATS.items() if box[0] == "Promotion" for f in formats
)

# Boxen, die nur mit gefuelltem Asset-Block laufen duerfen (Whitelist-Guard).
ASSET_GATED_BOXES = {
    ("Proof", "Selection"): "PROOF_ASSETS",
    ("Promotion", "Education"): "LEAD_MAGNETS",
    ("Promotion", "Selection"): "OFFERS",
}

# Format -> Asset-Config-Attribut (fuer die Asset-Injektion in den Prompt).
FORMAT_ASSET_ATTR = {
    "CaseProof": "PROOF_ASSETS",
    "Magnet": "LEAD_MAGNETS",
    "Offer": "OFFERS",
}

# Legacy-Formate: Verhalten ohne MATRIX-Config (Mandant ohne Matrix-Feature).
LEGACY_FORMATS = ("Opinion", "POV", "Signature", "Story")


def effective_boxes(cfg) -> list:
    """Deklarierte Boxen minus Boxen, deren Asset-Block leer ist.
    Mandant ohne MATRIX -> [] (Matrix-Feature aus)."""
    matrix = getattr(cfg, "MATRIX", None)
    if not matrix:
        return []
    boxes = []
    for box in matrix.get("boxes", []):
        box = tuple(box)
        attr = ASSET_GATED_BOXES.get(box)
        if attr and not getattr(cfg, attr, None):
            continue
        boxes.append(box)
    return boxes


def formats_for_box(box, cfg) -> list:
    """Kandidaten-Formate einer Ziel-Box (nur wenn die Box effektiv erlaubt ist)."""
    if tuple(box) not in effective_boxes(cfg):
        return []
    return list(BOX_FORMATS[tuple(box)])


def free_formats(cfg) -> list:
    """Format-Kandidaten fuer einen freien Best-Fit-Run: alle Formate der
    effektiven Boxen MINUS Promotion-Formate UND MINUS Asset-gated Formate
    (CaseProof/Magnet/Offer). Beide laufen ausschliesslich ueber ihren
    dedizierten Quota-/Asset-Pfad, nie ueber den generischen Free-Fill-Pool,
    damit Promotion-Kappe und Asset-Guard deterministisch halten.
    Ohne MATRIX -> die 4 Legacy-Formate."""
    boxes = effective_boxes(cfg)
    if not boxes:
        return list(LEGACY_FORMATS)
    return [
        f
        for box in boxes
        for f in BOX_FORMATS[box]
        if f not in PROMOTION_FORMATS and f not in FORMAT_ASSET_ATTR
    ]


def _window(recent_boxes: list) -> list:
    """Die letzten (bis zu) 10 KLASSIFIZIERTEN Boxen: erst filtern, dann
    schneiden: unklassifizierte Eintraege duerfen das Fenster nicht verkuerzen."""
    return [tuple(b) for b in recent_boxes if tuple(b) in BOX_FORMATS][:10]


def _row_deficits(window: list, mix: dict) -> dict:
    """Row -> Fehlbetrag gegen Soll (nur positive Defizite)."""
    counts = {job: 0 for job in JOBS}
    for job, _stage in window:
        if job in counts:
            counts[job] += 1
    return {job: max(0, mix.get(job, 0) - counts[job]) for job in JOBS}


def pick_target_box(recent_boxes: list, cfg):
    """Deterministische Ziel-Box gegen Mix 50/30/20 + Selection-Floor +
    Promotion-Kappe ueber die letzten 10 klassifizierten Posts.

    Regeln (Spec): <5 klassifiziert -> None. 5-9 -> nur Selection-Floor.
    10 -> volle Zeilen-Quota. Zeile defizitaer wenn actual < mix[row]-1.
    Floor vor Zeilen-Defizit; Promotion-Ziele entfallen ab Kappe.
    """
    matrix = getattr(cfg, "MATRIX", None)
    boxes = effective_boxes(cfg)
    if not matrix or not boxes:
        return None

    window = _window(recent_boxes)
    if len(window) < 5:
        return None

    mix = matrix["mix"]
    floor = matrix["selection_floor"]
    cap = matrix["promotion_cap"]
    promo_count = sum(1 for job, _ in window if job == "Promotion")
    selection_count = sum(1 for _, stage in window if stage == "Selection")
    deficits = _row_deficits(window, mix)

    def _promo_ok(box):
        return box[0] != "Promotion" or promo_count < cap

    # 1) Selection-Floor zuerst.
    if selection_count < floor:
        candidates = [b for b in boxes if b[1] == "Selection" and _promo_ok(b)]
        if candidates:
            # Zeile mit groesstem Defizit zuerst, Tie-Break = feste JOBS-Ordnung.
            candidates.sort(key=lambda b: (-deficits[b[0]], JOBS.index(b[0])))
            return candidates[0]

    # 2) Zeilen-Quota erst bei vollem Fenster.
    if len(window) < 10:
        return None

    deficient = [
        job for job in JOBS
        if sum(1 for j, _ in window if j == job) < mix.get(job, 0) - 1
    ]
    deficient = [j for j in deficient if j != "Promotion" or promo_count < cap]
    if not deficient:
        return None
    target_row = max(deficient, key=lambda j: (deficits[j], -JOBS.index(j)))

    # Innerhalb der Zeile: am wenigsten bespielter Stage, Tie = STAGES-Ordnung.
    row_boxes = [b for b in boxes if b[0] == target_row]
    if not row_boxes:
        return None
    stage_counts = {s: sum(1 for j, st in window if j == target_row and st == s)
                    for s in STAGES}
    row_boxes.sort(key=lambda b: (stage_counts[b[1]], STAGES.index(b[1])))
    return row_boxes[0]


def coverage_line(recent_boxes: list, cfg) -> str:
    """Log-Zeile: Ist gegen Soll ueber das aktuelle Fenster."""
    matrix = getattr(cfg, "MATRIX", None)
    if not matrix:
        return "Matrix: aus (keine MATRIX-Config)"
    window = _window(recent_boxes)
    mix = matrix["mix"]
    parts = [
        f"{job} {sum(1 for j, _ in window if j == job)}/{mix.get(job, 0)}"
        for job in JOBS
    ]
    sel = sum(1 for _, s in window if s == "Selection")
    parts.append(f"Selection {sel}/{matrix['selection_floor']}")
    return f"Coverage ({len(window)} Posts): " + " | ".join(parts)


def pick_asset(assets: list, recent_ids: list):
    """Least-recently-used Asset: erst nie genutzte, sonst das am laengsten
    nicht genutzte (recent_ids ist neuestes-zuerst). [] -> None."""
    if not assets:
        return None
    for asset in assets:
        if asset.get("id") not in recent_ids:
            return asset
    # Alle benutzt: das mit dem aeltesten (= letzten) Auftritt in recent_ids.
    return max(assets, key=lambda a: recent_ids.index(a["id"]))


def asset_for_format(post_format: str, cfg, recent_ids: list):
    """Asset fuer ein Asset-Format aus der Mandanten-Config. None wenn das
    Format kein Asset braucht oder der Block leer ist."""
    attr = FORMAT_ASSET_ATTR.get(post_format)
    if not attr:
        return None
    return pick_asset(getattr(cfg, attr, None) or [], recent_ids or [])


# Zahlen mit Einheit: Prozent, Waehrung, Vielfache. Reine Zaehl-Zahlen
# ("3 Schritte", Jahreszahlen) sind bewusst NICHT geschuetzt.
_FIGURE_RE = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:%|prozent|percent)"
    r"|(?:\u20ac|\$|\beur\b|\busd\b)\s*\d+(?:[.,]\d+)*"
    r"|\d+(?:[.,]\d+)*\s*(?:\u20ac|\beur\b|\busd\b|\bdollar\b)"
    r"|\d+(?:[.,]\d+)?\s*(?:x\b|-fach\b|fach\b|times\b)",
    re.IGNORECASE,
)


def extract_figures(text: str) -> set:
    """Alle Einheiten-Zahlen eines Texts, normalisiert (lowercase, ohne
    Leerzeichen, Komma -> Punkt)."""
    out = set()
    for m in _FIGURE_RE.finditer(text or ""):
        out.add(re.sub(r"\s+", "", m.group(0)).replace(",", ".").lower())
    return out


def figures_ok(text: str, asset: dict) -> bool:
    """Zahlen-Guard: jede Einheiten-Zahl im Draft muss aus dem gewaehlten
    Asset stammen (alle String-Felder des Assets zaehlen als Whitelist)."""
    allowed = set()
    for value in (asset or {}).values():
        if isinstance(value, str):
            allowed |= extract_figures(value)
    return extract_figures(text) <= allowed
